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

/**
 * LLM 호출 — 우선순위:
 *   1) LLM_PROXY_URL (need-only-prd FastAPI 백엔드 프록시, 기본 활성화)
 *   2) AOAI_ENDPOINT (원본 pfy-front 사내 게이트웨이, 직접 호출)
 *
 * LLM_PROXY_URL이 설정되어 있으면(기본값 http://localhost:8001/api/llm/chat-completion)
 * 우리 FastAPI 백엔드의 프록시 엔드포인트로 요청을 보낸다.
 * 이렇게 하면 사내 VPN/게이트웨이 접근이 불가능한 환경에서도 우리 백엔드가
 * 사용하는 Azure OpenAI(gpt-5.4)를 그대로 사용할 수 있다.
 */
export async function callLLM(messages: ChatMessage[], maxTokens = 1500): Promise<string> {
  const proxyUrl = process.env.LLM_PROXY_URL ?? 'http://localhost:8001/api/llm/chat-completion';
  const directEndpoint = process.env.AOAI_ENDPOINT;
  const directKey = process.env.AOAI_API_KEY;
  const useProxy = process.env.USE_LLM_PROXY !== 'false';  // 기본 true

  if (useProxy && proxyUrl) {
    const response = await fetch(proxyUrl, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        messages,
        temperature: 0.35,
        max_tokens: maxTokens,
        stream: false,
      }),
    });
    if (!response.ok) {
      const errText = await response.text().catch(() => '');
      throw new Error(`LLM Proxy 오류 (${response.status}): ${errText.slice(0, 300)}`);
    }
    const data = await response.json() as { choices?: { message?: { content?: string } }[] };
    const content = data.choices?.[0]?.message?.content;
    if (!content) {
      throw new Error(`LLM Proxy 응답에 content 없음: ${JSON.stringify(data).slice(0, 300)}`);
    }
    return content;
  }

  // 원본 AOAI 게이트웨이 직접 호출 (USE_LLM_PROXY=false로 명시적으로 껐을 때만)
  if (!directEndpoint || !directKey) {
    throw new Error(
      'LLM 호출 설정이 없습니다. LLM_PROXY_URL(기본) 또는 AOAI_ENDPOINT+AOAI_API_KEY 를 설정하세요.',
    );
  }
  const deployment = process.env.AOAI_DEPLOYMENT ?? 'gpt-5.2';
  const response = await fetch(directEndpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-Api-Key': directKey,
    },
    body: JSON.stringify({
      model: deployment,
      messages,
      temperature: 0.35,
      max_tokens: maxTokens,
      stream: false,
    }),
  });
  if (!response.ok) {
    const errText = await response.text().catch(() => '');
    throw new Error(`LLM API 오류 (${response.status}): ${errText.slice(0, 300)}`);
  }
  const data = await response.json() as { choices?: { message?: { content?: string } }[] };
  const content = data.choices?.[0]?.message?.content;
  if (!content) {
    throw new Error(`LLM 응답에서 content를 찾을 수 없습니다. 응답: ${JSON.stringify(data).slice(0, 300)}`);
  }
  return content;
}
