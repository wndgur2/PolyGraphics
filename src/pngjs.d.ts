/**
 * pngjs ships no types. Only the sliver used here is declared: a PNG of a
 * known size, filled and written synchronously.
 */
declare module "pngjs" {
  export class PNG {
    constructor(opts?: { width?: number; height?: number });
    width: number;
    height: number;
    data: Buffer;
    static sync: { write(png: PNG): Buffer; read(buf: Buffer): PNG };
  }
}
