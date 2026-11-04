import { Container, getContainer } from "@cloudflare/containers";

const KEEPALIVE_INTERVAL_MS = 5 * 60 * 1000;
const CONTAINER_HEALTH_PATH = "http://container/health";

const FORWARDED_ENV_KEYS = [
  "DATABASE_URL",
  "SALF1_BOT_TOKEN",
  "TELEGRAM_API_ID",
  "TELEGRAM_API_HASH",
  "TELEGRAM_OIDC_CLIENT_ID",
  "TELEGRAM_OIDC_CLIENT_SECRET",
  "SALF1_SESSION_ENCRYPTION_KEY",
  "SALF1_OWNER_USER_IDS",
  "SALF1_ADMIN_IDS",
  "SALF1_CREATOR_USERNAME",
  "SALF1_CHANNEL_USERNAME",
  "SALF1_EVENT_BRIDGE_URL",
  "SALF1_KEYWORD_ACK_URL",
  "SALF1_LOGIN_TOKEN_TTL_SECONDS",
  "SALF1_PAYMENT_URL",
  "SALF1_CARD_PAYMENT_URL",
  "SALF1_PAYMENT_SUPPORT_URL",
  "SALF1_REFERRAL_REWARD",
  "SALF1_TRIAL_HOURS",
  "SALF1_DB_POOL_MIN",
  "SALF1_DB_POOL_MAX",
  "SALF1_EMOJI_ACCOUNT",
  "SALF1_EMOJI_ACCOUNT_ALT",
  "SALF1_EMOJI_SELF",
  "SALF1_EMOJI_SELF_ALT",
  "SALF1_EMOJI_AUTOMATION",
  "SALF1_EMOJI_AUTOMATION_ALT",
  "SALF1_EMOJI_PROTECTION",
  "SALF1_EMOJI_PROTECTION_ALT",
  "SALF1_EMOJI_TOOLS",
  "SALF1_EMOJI_TOOLS_ALT",
  "SALF1_EMOJI_SYSTEM",
  "SALF1_EMOJI_SYSTEM_ALT",
  "SALF1_EMOJI_BALANCE",
  "SALF1_EMOJI_BALANCE_ALT",
  "SALF1_EMOJI_WARNING",
  "SALF1_EMOJI_WARNING_ALT",
];

function randomHex(byteLength = 48) {
  const bytes = crypto.getRandomValues(new Uint8Array(byteLength));
  return Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0")).join("");
}

async function getOrCreateSecret(storage, key) {
  let value = await storage.get(key);
  if (typeof value === "string" && value.length >= 32) {
    return value;
  }

  value = randomHex(48);
  await storage.put(key, value);
  return value;
}

function copyConfiguredEnv(source, target) {
  for (const key of FORWARDED_ENV_KEYS) {
    const value = source[key];
    if (typeof value === "string" && value.length > 0) {
      target[key] = value;
    }
  }
}

export class Salf1Container extends Container {
  defaultPort = 4173;
  requiredPorts = [4173];
  sleepAfter = "10m";
  enableInternet = true;

  constructor(ctx, env) {
    super(ctx, env);
    this.runtimeEnv = env;
    this.runtimeConfigPromise = null;
    this.keepaliveSetupPromise = null;
  }

  async configureRuntime(request) {
    if (this.runtimeConfigPromise) return this.runtimeConfigPromise;

    this.runtimeConfigPromise = (async () => {
    const requestUrl = new URL(request.url);
    const publicOrigin = String(
      this.runtimeEnv.PUBLIC_ORIGIN || requestUrl.origin,
    ).replace(/\/+$/, "");
    const publicHost = new URL(publicOrigin).hostname;

    const [sessionSecret, workerApiToken, webhookSecret] = await Promise.all([
      getOrCreateSecret(this.ctx.storage, "secret:session"),
      getOrCreateSecret(this.ctx.storage, "secret:worker-api"),
      getOrCreateSecret(this.ctx.storage, "secret:webhook"),
    ]);

    const vars = {
      NODE_ENV: "production",
      PORT: "4173",
      SALF1_PORT: "8080",
      SALF1_ROLE: String(this.runtimeEnv.SALF1_ROLE || "all"),
      SALF1_WORKER_URL: "http://127.0.0.1:8080",
      SALF1_LOGIN_BASE_URL: publicOrigin,
      PUBLIC_ORIGIN: publicOrigin,
      RP_ID: String(this.runtimeEnv.RP_ID || publicHost),
      TELEGRAM_OIDC_REDIRECT_URI: String(
        this.runtimeEnv.TELEGRAM_OIDC_REDIRECT_URI ||
          publicOrigin + "/auth/telegram/callback",
      ),
      SESSION_SECRET: String(this.runtimeEnv.SESSION_SECRET || "") || sessionSecret,
      WORKER_API_TOKEN: String(this.runtimeEnv.WORKER_API_TOKEN || "") || workerApiToken,
      SALF1_WEBHOOK_SECRET: String(this.runtimeEnv.SALF1_WEBHOOK_SECRET || "") || webhookSecret,
    };

    copyConfiguredEnv(this.runtimeEnv, vars);
    // Runtime-critical values must not be overridden by user-provided vars.
    vars.NODE_ENV = "production";
    vars.PORT = "4173";
    vars.SALF1_PORT = "8080";
    vars.SALF1_ROLE = String(this.runtimeEnv.SALF1_ROLE || "all");
    vars.SALF1_WORKER_URL = "http://127.0.0.1:8080";
    vars.SALF1_LOGIN_BASE_URL = publicOrigin;
    vars.PUBLIC_ORIGIN = publicOrigin;
    vars.RP_ID = String(this.runtimeEnv.RP_ID || publicHost);
    vars.TELEGRAM_OIDC_REDIRECT_URI = String(
      this.runtimeEnv.TELEGRAM_OIDC_REDIRECT_URI ||
        publicOrigin + "/auth/telegram/callback",
    );

    this.envVars = vars;
    })();

    try {
      await this.runtimeConfigPromise;
    } catch (error) {
      this.runtimeConfigPromise = null;
      throw error;
    }
  }

  async scheduleKeepalive() {
    if (this.keepaliveSetupPromise) return this.keepaliveSetupPromise;

    this.keepaliveSetupPromise = (async () => {
      const scheduledAt = await this.ctx.storage.getAlarm();
      if (scheduledAt === null) {
        await this.ctx.storage.setAlarm(Date.now() + KEEPALIVE_INTERVAL_MS);
      }
    })().catch(error => {
      this.keepaliveSetupPromise = null;
      throw error;
    });

    return this.keepaliveSetupPromise;
  }

  async fetch(request) {
    await this.configureRuntime(request);
    await this.scheduleKeepalive();
    return super.fetch(request);
  }

  async alarm() {
    try {
      // A request every five minutes renews the ten-minute idle timer.
      // This keeps the bot process alive between Telegram updates.
      await super.fetch(new Request(CONTAINER_HEALTH_PATH));
    } catch (error) {
      console.error(
        "SALF1 container keepalive failed:",
        String(error?.message || error).slice(0, 240),
      );
    } finally {
      await this.ctx.storage.setAlarm(Date.now() + KEEPALIVE_INTERVAL_MS);
    }
  }
}

export default {
  async fetch(request, env) {
    const container = getContainer(env.SALF1_CONTAINER, "salf1-primary");
    return container.fetch(request);
  },
};
