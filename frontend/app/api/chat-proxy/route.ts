import { NextRequest } from "next/server";

export async function POST(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const analysisId = searchParams.get("analysisId");

  if (!analysisId) {
    return new Response("Missing analysisId", { status: 400 });
  }

  const body = await req.json();
  const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

  const upstream = await fetch(`${apiUrl}/api/chat/${analysisId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message: body.messages?.at(-1)?.content || "" }),
  });

  return new Response(upstream.body, {
    headers: { "Content-Type": "text/event-stream" },
  });
}
