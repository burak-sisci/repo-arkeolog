import { NextRequest, NextResponse } from "next/server";

/** Node gerekli: ReadableStream gövde ve SSE için */
export const runtime = "nodejs";

const UPSTREAM = (process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").replace(/\/$/, "");

function forwardHeaders(incoming: Headers): Headers {
  const out = new Headers(incoming);
  ["host", "connection", "keep-alive", "transfer-encoding", "content-length"].forEach((k) => out.delete(k));
  return out;
}

async function proxy(req: NextRequest, pathSegments: string[] | undefined): Promise<NextResponse> {
  const sub = pathSegments?.length ? pathSegments.join("/") : "";
  const target = `${UPSTREAM}/api/${sub}${req.nextUrl.search}`;

  const method = req.method;
  const hasBody = !["GET", "HEAD"].includes(method);

  try {
    const init: RequestInit & { duplex?: string } = {
      method,
      headers: forwardHeaders(req.headers),
    };
    if (hasBody) {
      init.body = req.body;
      init.duplex = "half";
    }

    const upstream = await fetch(target, init);

    const outHeaders = new Headers(upstream.headers);
    outHeaders.delete("transfer-encoding");

    return new NextResponse(upstream.body, {
      status: upstream.status,
      statusText: upstream.statusText,
      headers: outHeaders,
    });
  } catch {
    return NextResponse.json(
      {
        detail:
          "Backend API'ye bağlanılamıyor. FastAPI sürecinin ayakta olduğundan emin olun (varsayılan http://127.0.0.1:8000).",
      },
      { status: 503 },
    );
  }
}

type RouteCtx = { params: { path?: string[] } };

export async function GET(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx.params.path);
}

export async function POST(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx.params.path);
}

export async function PUT(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx.params.path);
}

export async function PATCH(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx.params.path);
}

export async function DELETE(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx.params.path);
}

export async function HEAD(req: NextRequest, ctx: RouteCtx) {
  return proxy(req, ctx.params.path);
}

export async function OPTIONS() {
  return new NextResponse(null, {
    status: 204,
    headers: {
      "Access-Control-Allow-Origin": "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS",
      "Access-Control-Allow-Headers": "*",
    },
  });
}
