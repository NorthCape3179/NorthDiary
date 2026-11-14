import { Container, Graphics, Sprite, Texture } from 'pixi.js';
import { WaterSystem } from './WaterSystem';

interface Duck {
  body: Sprite;
  reflection: Sprite;
  active: boolean;
  entered: boolean;
  x: number;
  y: number;
  speed: number;
  heading: number;
  turnAtX: number | null;
  turnRemaining: number;
}

const DUCK_GROUPS = [[0], [1], [0, 1], [0, 0, 1], [1, 1, 0], [0, 0, 0, 1, 1]];
const TURN_DURATION = 1.4;

export class LakeWildlifeSystem {
  private readonly wakes = new Graphics();
  private readonly wakeWaves = Array.from({length: 40}, () => ({x:0, y:0, age:4, direction:1}));
  private wakeClock = 0;
  private readonly splash = new Graphics();
  private readonly ducks: Duck[] = [];
  private readonly fish = new Sprite();
  private duckAge = -1;
  private fishAge = -1;
  private duckWait = 3;
  private fishWait = 8;
  private fishX = 240;
  private fishY = 198;
  private fishDirection = 1;
  private landed = false;

  constructor(layer: Container, private textures: Texture[], private water: WaterSystem) {
    layer.addChild(this.wakes);
    for (let index = 0; index < 5; index++) {
      const texture = textures[0];
      const body = new Sprite(texture);
      const reflection = new Sprite(texture);
      body.anchor.set(.5, .88);
      reflection.anchor.set(.5, .88);
      reflection.alpha = .16;
      body.visible = reflection.visible = false;
      layer.addChild(reflection, body);
      this.ducks.push({body, reflection, active:false, entered:false, x:0, y:0,
                       speed:0, heading:0, turnAtX:null, turnRemaining:0});
    }
    this.fish.anchor.set(.5);
    this.fish.visible = false;
    layer.addChild(this.fish, this.splash);
  }

  update(dt: number) {
    this.updateDucks(dt);
    this.drawWakeWaves(dt);
    this.updateFish(dt);
  }

  private drawWakeWaves(dt: number) {
    for (const wave of this.wakeWaves) {
      wave.age += dt;
      if (wave.age >= 4) continue;
      const radius = 2 + wave.age * 5;
      const alpha = .48 * Math.pow(1 - wave.age / 4, 1.3);
      for (let i = 0; i <= 26; i++) {
        if (i % 9 === 0) continue;
        const angle = Math.PI * (.5 + i / 26);
        const x = wave.x + wave.direction * Math.cos(angle) * radius;
        const y = wave.y + Math.sin(angle) * radius * .31;
        this.wakes.rect(x, y, 1.1, .65).fill({color:0xd5e6dd, alpha});
      }
    }
  }

  private updateDucks(dt: number) {
    this.wakes.clear();
    if (this.duckAge < 0) {
      this.duckWait -= dt;
      if (this.duckWait > 0) return;
      this.duckAge = 0;
      const direction = Math.random() < .5 ? 1 : -1;
      const group = DUCK_GROUPS[Math.floor(Math.random() * DUCK_GROUPS.length)];
      for (const [index, duck] of this.ducks.entries()) {
        duck.active = index < group.length;
        duck.body.visible = duck.reflection.visible = duck.active;
        if (!duck.active) continue;
        duck.body.texture = duck.reflection.texture = this.textures[group[index]];
        duck.x = direction > 0 ? -18 - Math.random() * 75 : 498 + Math.random() * 75;
        duck.y = 160 + Math.random() * 34;
        duck.speed = 3.7 + Math.random() * 2;
        duck.heading = direction > 0 ? 0 : Math.PI;
        duck.entered = false;
        // One Bernoulli draw per individual per visit, never per frame.
        duck.turnAtX = Math.random() < .2 ? 110 + Math.random() * 260 : null;
        duck.turnRemaining = 0;
      }
    }
    this.duckAge += dt;
    this.wakeClock += dt;
    const emitWave = this.wakeClock >= .72;
    if (emitWave) this.wakeClock %= .72;
    for (const [index, duck] of this.ducks.entries()) {
      if (!duck.active) continue;
      const {body, reflection} = duck;
      const directionBeforeTurn = Math.cos(duck.heading) >= 0 ? 1 : -1;
      if (duck.turnAtX !== null && (duck.x - duck.turnAtX) * directionBeforeTurn >= 0) {
        duck.turnAtX = null;
        duck.turnRemaining = TURN_DURATION;
      }
      if (duck.turnRemaining > 0) {
        const step = Math.min(dt, duck.turnRemaining);
        duck.heading += Math.PI * step / TURN_DURATION;
        duck.turnRemaining -= step;
      }
      const facing = Math.cos(duck.heading);
      const direction = facing >= 0 ? 1 : -1;
      duck.x += facing * duck.speed * dt;
      const x = duck.x;
      const y = duck.y + Math.sin(duck.heading) * .8;
      if (x >= 0 && x <= 480) duck.entered = true;
      if (duck.entered && (x < -30 || x > 510)) {
        duck.active = false;
        body.visible = reflection.visible = false;
        continue;
      }
      const width = 12 + (y - 165) * .16;
      body.visible = reflection.visible = true;
      body.width = width;
      body.height = width * body.texture.height / body.texture.width;
      body.scale.x = width / body.texture.width * facing;
      body.position.set(x, y + Math.sin(this.duckAge * 1.7 + index) * .24);
      body.rotation = Math.sin(this.duckAge * 1.3 + index) * .016;
      reflection.scale.set(body.scale.x, -Math.abs(body.scale.y) * .27);
      reflection.position.set(x, y + .7);
      if (emitWave && x > 0 && x < 480) {
        const wave = this.wakeWaves.find(item => item.age >= 4);
        if (wave) Object.assign(wave, {x:x - direction * 3, y, age:0, direction});
      }
      // Short broken V-shaped wake trails behind each bird.
      for (let step = 0; step < 9; step++) {
        const tailX = x - direction * (5 + step * 1.6);
        const spread = .35 + step * .23;
        const alpha = (.43 - step * .039) * (.8 + .2 * Math.sin(this.duckAge * 3 - step));
        for (const side of [-1, 1]) {
          this.wakes.rect(tailX, y + side * spread, 1.6, .65).fill({color:0xc5d9d8, alpha});
        }
      }
    }
    if (this.ducks.every(duck => !duck.active)) {
      this.duckAge = -1;
      this.duckWait = 120 + Math.random() * 160;
      for (const duck of this.ducks) duck.body.visible = duck.reflection.visible = false;
      this.wakes.clear();
    }
  }

  private updateFish(dt: number) {
    this.splash.clear();
    if (this.fishAge < 0) {
      this.fishWait -= dt;
      if (this.fishWait > 0) return;
      this.fishAge = 0;
      this.fishX = 90 + Math.random() * 300;
      this.fishY = 183 + Math.random() * 33;
      this.fishDirection = Math.random() < .5 ? 1 : -1;
      this.landed = false;
      this.water.add(this.fishX, this.fishY);
    }
    this.fishAge += dt;
    const leapDuration = 1.15;
    const progress = Math.min(1, this.fishAge / leapDuration);
    const landingX = this.fishX + this.fishDirection * 17;
    this.fish.visible = this.fishAge < leapDuration;
    if (this.fish.visible) {
      this.fish.texture = this.textures[progress < .5 ? 2 : 3];
      const width = 6 + (this.fishY - 183) * .09;
      this.fish.width = width;
      this.fish.height = width * this.fish.texture.height / this.fish.texture.width;
      this.fish.scale.x = Math.abs(this.fish.scale.x) * this.fishDirection;
      this.fish.position.set(this.fishX + this.fishDirection * 17 * progress,
                             this.fishY - Math.sin(progress * Math.PI) * 9);
      this.fish.rotation = (progress - .5) * .6 * this.fishDirection;
    }
    if (!this.landed && this.fishAge >= leapDuration) {
      this.landed = true;
      this.water.add(landingX, this.fishY);
    }
    const splashAge = this.fishAge - leapDuration;
    if (splashAge >= 0 && splashAge < .85) {
      for (let index = 0; index < 7; index++) {
        const velocityX = (index - 3) * 2;
        const velocityY = -7 - (index % 3) * 3;
        const x = landingX + velocityX * splashAge;
        const y = this.fishY + velocityY * splashAge + 18 * splashAge * splashAge;
        this.splash.rect(x, y, .65, .9).fill({color:0xe0e9df, alpha:(1 - splashAge / .85) * .75});
      }
    }
    if (this.fishAge >= leapDuration + .9) {
      this.fishAge = -1;
      this.fishWait = 42 + Math.random() * 50;
      this.splash.clear();
    }
  }
}
