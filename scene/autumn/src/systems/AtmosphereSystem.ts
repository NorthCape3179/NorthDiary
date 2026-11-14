import { Container, Sprite, Texture } from 'pixi.js';

function randomFrom(seed: number) {
  return () => {
    seed = (Math.imul(seed, 1664525) + 1013904223) >>> 0;
    return seed / 4294967296;
  };
}

// Draw at scene pixel scale so the edges match the stepped shapes in the painting.
function cloudPixels(ctx: CanvasRenderingContext2D, seed: number, width: number, height: number) {
  const random = randomFrom(seed);
  const pixels = ctx.createImageData(width, height);
  const towers = [
    [.23, .34, .19, .26],
    [.49, .29, .20, .27],
    [.72, .43, .18, .20],
    [.87, .53, .13, .11],
  ].map(([x, y, rx, ry]) => ({
    x: x + (random() - .5) * .14,
    y: y + (random() - .5) * .20,
    rx: rx * (.76 + random() * .48),
    ry: ry * (.77 + random() * .46),
  }));
  const wisps = Array.from({ length: 13 }, () => ({
    x: .03 + random() * .94,
    y: .48 + random() * .43,
    rx: .013 + random() * .092,
    ry: .017 + random() * .042,
  }));
  const field = (x: number, y: number, shapes: typeof towers) => {
    let density = -1;
    for (const s of shapes) {
      const dx = (x - s.x) / s.rx;
      const dy = (y - s.y) / s.ry;
      density = Math.max(density, 1 - dx * dx - dy * dy);
    }
    return density;
  };
  const cream = [238, 228, 206];
  const shade = [203, 212, 219];
  const mid = [222, 220, 207];
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      const u = (x + .5) / width;
      const v = (y + .5) / height;
      const scallop = .11 * Math.sin(x * 1.36 + seed) + .09 * Math.sin(x * .63 + y * 2.4);
      const body = field(u, v, towers) + scallop;
      const wisp = field(u, v, wisps);
      if (body <= 0 && wisp <= 0) continue;
      const shadow = field(u + .037, v - .09, towers);
      const rgb = body <= 0 ? (v < .68 ? mid : shade)
        : shadow > .35 && v > .34 ? shade : shadow > .08 && v > .26 ? mid : cream;
      const alpha = body > 0 ? (body < .12 ? 215 : 255) : 155 + Math.round(wisp * 57);
      pixels.data.set([...rgb, alpha], (y * width + x) * 4);
    }
  }
  ctx.putImageData(pixels, 0, 0);
}

function formation(seed: number, width: number, height: number, mist: boolean) {
  const random = randomFrom(seed);
  const canvas = document.createElement('canvas');
  canvas.width = width;
  canvas.height = height;
  const ctx = canvas.getContext('2d')!;
  if (!mist) {
    cloudPixels(ctx, seed, width, height);
    const texture = Texture.from(canvas);
    texture.source.scaleMode = 'nearest';
    return texture;
  }
  const count = 5 + seed % 3;
  const lobes = Array.from({ length: count }, () => ({
    x: width * (.24 + random() * .52),
    y: height * (.25 + random() * .48),
    rx: width * (.12 + random() * .14),
    ry: height * (.19 + random() * .18),
  }));
  const pixels = ctx.createImageData(width, height);
  for (let y = 0; y < height; y++) {
    for (let x = 0; x < width; x++) {
      let density = 0;
      for (const lobe of lobes) {
        const dx = (x - lobe.x) / lobe.rx;
        const dy = (y - lobe.y) / lobe.ry;
        density = Math.max(density, 1 - dx * dx - dy * dy);
      }
      const grain = random();
      density = Math.max(0, density - grain * .19);
      const edge = Math.min(1, x / 5, (width - 1 - x) / 5, y / 2, (height - 1 - y) / 2);
      const alpha = edge * Math.min(1, density * 1.1);
      const light = y / height + grain * .22 < .66;
      const rgb = light ? [239, 241, 237] : [193, 208, 224];
      pixels.data.set([...rgb, Math.round(alpha * 255)], (y * width + x) * 4);
    }
  }
  ctx.putImageData(pixels, 0, 0);
  const texture = Texture.from(canvas);
  texture.source.scaleMode = 'nearest';
  return texture;
}

// x, y, width, height, drift speed, opacity
const CLOUDS = [
  [88, 17, 55, 15, .52, .70], [189, 11, 82, 25, .67, .83],
  [290, 29, 47, 12, .43, .68], [347, 17, 69, 22, .62, .77],
  [432, 33, 66, 18, .38, .61], [-30, 37, 78, 19, .46, .63],
  [17, 22, 42, 10, .59, .56], [258, 6, 34, 9, .74, .52],
];
const MIST = [
  [80, 82, 36, 24, .55, .58], [137, 72, 31, 21, .46, .54],
  [176, 90, 39, 26, .68, .63], [226, 96, 35, 23, .57, .62],
  [267, 98, 30, 22, .43, .58], [306, 87, 32, 24, .61, .56],
  [348, 77, 29, 20, .50, .52], [29, 79, 33, 23, .44, .52],
];

export class AtmosphereSystem {
  private readonly textures: Texture[] = [];
  private readonly motions: Array<(time: number) => void> = [];

  constructor(cloudLayer: Container, mistLayer: Container) {
    for (const [mist, layer, forms] of [[false, cloudLayer, CLOUDS], [true, mistLayer, MIST]] as const) {
      forms.forEach(([x, y, width, height, speed, opacity], index) => {
        const texture = formation((mist ? 8917 : 2311) + index * 9931, width, height, mist);
        this.textures.push(texture);
        const sprite = new Sprite({ texture, roundPixels: false });
        layer.addChild(sprite);
        const phase = index * 2.39;
        const span = 480 + width + 36;
        this.motions.push(time => {
          // Cloud loops cross the viewport boundary entirely off screen.
          // Mist stays within its valley, fading gently as it drifts.
          const drift = (.25 + index * .097 + time * speed / 38) % 1;
          sprite.x = mist ? x + (drift - .5) * 38
                          : (x + width + 18 + time * speed) % span - width - 18;
          sprite.y = y + (mist ? 1.6 : .85) * Math.sin(time * .038 + phase);
          sprite.alpha = opacity * (mist ? Math.min(1, drift * 6, (1 - drift) * 6) : 1);
        });
      });
    }
    this.update(0);
  }

  update(time: number) {
    for (const move of this.motions) move(time);
  }

  destroy() {
    for (const texture of this.textures) texture.destroy(true);
  }
}


