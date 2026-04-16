export type ChatMessage = { role: 'system' | 'user' | 'assistant'; content: string };

/** LLM 응답에서 JSON 객체 블록 추출 */
export function extractJson(raw: string): unknown {
  const stripped = raw.replace(/```(?:json)?\s*/gi, '').replace(/```/g, '').trim();
  const start = stripped.indexOf('{');
  const end   = stripped.lastIndexOf('}');
  if (start === -1 || end === -1) {
    throw new Error(`응답에서 JSON을 찾을 수 없습니다. 응답 내용: ${stripped.slice(0, 200)}`);
  }
  return JSON.parse(stripped.slice(start, end + 1));
}

/** AOAI 호환 게이트웨이 (X-Api-Key, OpenAI chat 형식) */
export async function callLLM(messages: ChatMessage[], maxTokens = 1500): Promise<string> {
  const endpoint   = process.env.AOAI_ENDPOINT;
  const apiKey     = process.env.AOAI_API_KEY;
  const deployment = process.env.AOAI_DEPLOYMENT ?? 'gpt-5.2';

  if (!endpoint || !apiKey) {
    throw new Error(
      'AOAI 환경변수가 설정되지 않았습니다. scaffolding/.env 파일에 AOAI_ENDPOINT, AOAI_API_KEY 를 설정한 뒤 서버를 재시작하세요.',
    );
  }

  const response = await fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Api-Key': apiKey,
    },
    body: JSON.stringify({
      model:       deployment,
      messages,
      temperature: 0.35,
      max_tokens:  maxTokens,
      stream:      false,
    }),
  });

  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    throw new Error(`LLM API 오류 (${response.status}): ${errText.slice(0, 300)}`);
  }

  const data = await response.json() as {
    choices?: { message?: { content?: string } }[];
  };

  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error(`LLM 응답에서 content를 찾을 수 없습니다. 응답: ${JSON.stringify(data).slice(0, 300)}`);
  }
  return content;
}
