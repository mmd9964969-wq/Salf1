import test from "node:test";
import assert from "node:assert/strict";
import { createHmac } from "node:crypto";
import { validateTelegramMiniAppInitData } from "../lib/telegram-miniapp-auth.js";

const BOT_TOKEN = "123456789:TEST_BOT_TOKEN_FOR_UNIT_TESTS_ONLY";
const NOW = 1_800_000_000;

function makeInitData(overrides = {}) {
  const values = {
    auth_date: String(NOW - 60),
    query_id: "AAEAAAE",
    user: JSON.stringify({
      id: 987654321,
      first_name: "Test",
      last_name: "User",
      username: "test_user",
    }),
    ...overrides,
  };

  const entries = Object.entries(values).sort(([a], [b]) => a.localeCompare(b));
  const dataCheckString = entries.map(([key, value]) => key + "=" + value).join("\n");
  const secretKey = createHmac("sha256", "WebAppData").update(BOT_TOKEN).digest();
  const hash = createHmac("sha256", secretKey).update(dataCheckString).digest("hex");
  return new URLSearchParams([...entries, ["hash", hash]]).toString();
}

test("accepts valid Telegram Mini App initData", () => {
  const user = validateTelegramMiniAppInitData(makeInitData(), BOT_TOKEN, {
    nowSeconds: NOW,
  });
  assert.equal(user.id, "987654321");
  assert.equal(user.username, "test_user");
  assert.equal(user.first_name, "Test");
});

test("rejects a modified payload", () => {
  const initData = makeInitData().replace("test_user", "attacker");
  assert.throws(
    () => validateTelegramMiniAppInitData(initData, BOT_TOKEN, { nowSeconds: NOW }),
    { message: "MINI_APP_SIGNATURE_INVALID" },
  );
});

test("rejects expired initData", () => {
  const initData = makeInitData({ auth_date: String(NOW - 90_000) });
  assert.throws(
    () => validateTelegramMiniAppInitData(initData, BOT_TOKEN, { nowSeconds: NOW }),
    { message: "MINI_APP_DATA_EXPIRED" },
  );
});

test("rejects future-dated initData", () => {
  const initData = makeInitData({ auth_date: String(NOW + 120) });
  assert.throws(
    () => validateTelegramMiniAppInitData(initData, BOT_TOKEN, { nowSeconds: NOW }),
    { message: "MINI_APP_DATA_EXPIRED" },
  );
});

test("rejects duplicate fields", () => {
  const initData = makeInitData() + "&user=%7B%22id%22%3A1%7D";
  assert.throws(
    () => validateTelegramMiniAppInitData(initData, BOT_TOKEN, { nowSeconds: NOW }),
    { message: "MINI_APP_DUPLICATE_FIELD" },
  );
});

test("rejects missing bot token", () => {
  assert.throws(
    () => validateTelegramMiniAppInitData(makeInitData(), "", { nowSeconds: NOW }),
    { message: "MINI_APP_AUTH_NOT_CONFIGURED" },
  );
});
