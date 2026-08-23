/** Constant-time string compare. Length mismatch still walks the secret. */
export function timingSafeEqual(a: string, b: string): boolean {
    const aBuf = new TextEncoder().encode(a);
    const bBuf = new TextEncoder().encode(b);
    const len = Math.max(aBuf.length, bBuf.length, 1);
    let diff = aBuf.length ^ bBuf.length;
    for (let i = 0; i < len; i++) {
      const av = i < aBuf.length ? aBuf[i] : 0;
      const bv = i < bBuf.length ? bBuf[i] : 0;
      diff |= av ^ bv;
    }
    return diff === 0;
  }
  