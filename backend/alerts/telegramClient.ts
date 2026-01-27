/**
 * Telegram Client for Coin87 Alert Dispatcher
 *
 * Simple, stateless HTTP client for sending messages via Telegram Bot API.
 * Uses fetch (Node 18+) or node-fetch for older versions.
 */

declare const process: { env: Record<string, string | undefined> };

export type TelegramConfig = {
  botToken: string;
  channelId: string;
};

export type SendResult = {
  ok: boolean;
  messageId?: number;
  error?: string;
};

function validateConfig(config: TelegramConfig): void {
  if (!config.botToken || config.botToken.trim() === "") {
    throw new Error("TELEGRAM_BOT_TOKEN is required");
  }
  if (!config.channelId || config.channelId.trim() === "") {
    throw new Error("TELEGRAM_CHANNEL_ID is required");
  }
}

/**
 * Send a plain text message to the configured Telegram channel.
 *
 * - No markdown formatting (parse_mode omitted)
 * - Disable link preview to keep messages clean
 * - Silent notifications disabled (alerts should notify)
 */
export async function sendTelegramMessage(
  config: TelegramConfig,
  text: string,
): Promise<SendResult> {
  validateConfig(config);

  const url = `https://api.telegram.org/bot${config.botToken}/sendMessage`;

  const body = {
    chat_id: config.channelId,
    text: text,
    disable_web_page_preview: true,
  };

  try {
    const response = await fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(body),
    });

    const data = await response.json() as {
      ok: boolean;
      result?: { message_id: number };
      description?: string;
    };

    if (data.ok) {
      return {
        ok: true,
        messageId: data.result?.message_id,
      };
    }

    return {
      ok: false,
      error: data.description || "Unknown Telegram API error",
    };
  } catch (err) {
    const message = err instanceof Error ? err.message : "Network error";
    return {
      ok: false,
      error: message,
    };
  }
}

/**
 * Load Telegram config from environment variables.
 */
export function loadTelegramConfig(): TelegramConfig {
  const botToken = process.env.TELEGRAM_BOT_TOKEN || "";
  const channelId = process.env.TELEGRAM_CHANNEL_ID || "";

  return { botToken, channelId };
}
