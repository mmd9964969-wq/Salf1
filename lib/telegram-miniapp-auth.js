import { createHmac, timingSafeEqual } from "node:crypto";

const DEFAULT_MAX_AGE_SECONDS = 24 * 60 * 60;
const MAX_INIT_DATA_LENGTH = 16_384;

export function validateTelegramMiniAppInitData(
  rawInitData,
  botToken,
  {
    nowSeconds = Math.floor(Date.now() / 1000),
    maxAgeSeconds = DEFAULT_MAX_AGE_SECONDS,
  } = {},
) {
  const initData = String(rawInitData || "");
  const token = String(botToken || "").trim();

  if (!initData || initData.length > MAX_INIT_DATA_LENGTH) {
    throw new Error("MINI_APP_DATA_INVALID");
  }
  if (!token) {
    throw new Error("MINI_APP_AUTH_NOT_CONFIGURED");
  }

  const params = new URLSearchParams(initData);
  const entries = [...params.entries()];
  const keys = new Set();

  for (const [key] of entries) {
    if (keys.has(key)) throw new Error("MINI_APP_DUPLICATE_FIELD");
    keys.add(key);
  }

  const suppliedHash = String(params.get("hash") || "");
  if (!/^[a-f0-9]{64}$/i.test(suppliedHash)) {
    throw new Error("MINI_APP_HASH_INVALID");
  }

  const dataCheckString = entries
    .filter(([key]) => key !== "hash")
    .sort(([left], [right]) => left < right ? -1 : left > right ? 1 : 0)
    .map(([key, value]) => key + "=" + value)
    .join("\n");

  // Telegram Mini Apps HMAC validation:
  // secret_key = HMAC_SHA256(key="WebAppData", message=botToken)
  // calculated = HMAC_SHA256(key=secret_key, message=dataCheckString)
  const secretKey = createHmac("sha256", "WebAppData").update(token).digest();
  const calculatedHash = createHmac("sha256", secretKey)
    .update(dataCheckString)
    .digest();
  const receivedHash = Buffer.from(suppliedHash, "hex");

  if (
    receivedHash.length !== calculatedHash.length ||
    !timingSafeEqual(receivedHash, calculatedHash)
  ) {
    throw new Error("MINI_APP_SIGNATURE_INVALID");
  }

  const authDate = Number(params.get("auth_date"));
  if (
    !Number.isSafeInteger(authDate) ||
    authDate > nowSeconds + 60 ||
    nowSeconds - authDate > maxAgeSeconds
  ) {
    throw new Error("MINI_APP_DATA_EXPIRED");
  }

  let user;
  try {
    user = JSON.parse(params.get("user") || "null");
  } catch {
    throw new Error("MINI_APP_USER_INVALID");
  }

  const userId = String(user?.id ?? "");
  if (!/^\d{1,20}$/.test(userId)) {
    throw new Error("MINI_APP_USER_INVALID");
  }

  return {
    id: userId,
    username: String(user.username || ""),
    first_name: String(user.first_name || ""),
    last_name: String(user.last_name || ""),
    photo_url: String(user.photo_url || ""),
  };
}
