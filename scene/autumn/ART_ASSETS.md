# 秋日湖畔 0.3.0 美术素材与生成说明

使用内置 **imagegen** 制作，未使用需要 API Key 的 CLI。概念图只作参考，实际渲染使用独立的底图、透明枫枝和透明岩岸，没有把一张完整场景图伪装成可动分层。

## 文件

- `public/assets/autumn_day/autumn-background-v2.png`：1672×941，天空、群山、远岸树林和基础湖面合成的静态底图。没有前景枫枝、近岸岩石或芦苇。
- `public/assets/autumn_day/maple-canopy-v2.png`：1914×822，RGBA 独立透明枫枝，在两侧以不同尺寸和镜像布局。整个枫枝极轻摆动；另有独立 SVG 叶片脱落，不声称 PNG 内每片叶子均已拆分。
- `public/assets/autumn_day/shore-v2.png`：1672×941，RGBA 透明近岸岩石和短草，仅放在底部两角。
- 原有 `leaf0.svg` 至 `leaf9.svg`、芦苇茎与穗保持独立实体与根部 pivot。
- 概念参考图另存工作区 `outputs/autumn-art-concept-v2.png`，不作为运行时完整背景。

PNG 经实际窗口组合确认透明，无黑色背景。保留生成分辨率，在逻辑坐标 480×270 的三倍渲染画布上绘制，使用 nearest 纹理采样；没有将素材离线压成粗糙的 480px 位图。

远景底图内天空、山、森林并非独立可动图层。水面动画是对底图水域进行局部透明行位移，加独立波纹与漂叶；只处理配置中的水域，不对整张画面做扭曲。枫枝 PNG 是可替换部件，不是逐片分离的完整骨骼素材。此处说明实际层级，便于后续继续精修。

## 最终生成提示词集

概念参考（新生成，不使用用户截图作成品）：

> A handcrafted 16-bit / 32-bit Japanese indie-game autumn lake ambience scene, landscape 16:9. Broad tranquil muted dark teal lake in the lower 45%, irregular layered misty desaturated blue-grey mountains, intricate varied autumn maple forest at the far shoreline. Golden ochre, terracotta, crimson and wine-red leaves. Pale grey-blue afternoon sky, not sunset. Elegant maple twigs entering only from top corners, sparse near rocks and reeds at bottom corners. Clear pixel clusters, consistent virtual 640×360 pixel density, limited harmonious palette, quiet negative space in lower center. No text, UI, borders, humans, buildings, smooth brush textures, noise or photorealism. Composition reference only; actual background and animated components are separate.

底图（以概念图为编辑目标）：

> Edit target: the supplied autumn lake concept art. Produce the CLEAN STATIC BACKGROUND PLATE for this exact game scene, keeping its gorgeous crafted pixel-art style, color palette, lighting, exact horizon height around 53% and every background mountain, forest and lake reflection as unchanged as possible. REMOVE ALL overhanging foreground maple branches and foreground leaves at top left and top right, seamlessly repaint the sky and mountains behind them. REMOVE ALL near-bank rocks, mud, grasses, reeds and foreground floating maple leaves along the entire bottom and side corners, replacing these areas with continuous calm teal-blue lake that matches neighboring water. Retain the distant far-shore rocks, which are part of the background. No airborne leaves. The output must contain ONLY the clear cool blue-grey sky, layered atmospheric irregular blue mountains, intricate distant autumn mixed maple forest and its horizontal reflected shapes across the middle, and broad calm lake down to every bottom edge. Keep center lower lake especially quiet and dark teal for readable later lyrics. Do not add new scenery or objects. No typography, UI, border or watermark. Same 16:9 wide composition, full bleed. This is an actual runtime background layer to combine with separately editable moving branch, leaf, water and reed layers later, so absolutely no foreground branches/reeds/near rocks should remain.

枫枝（新生成；概念图仅作风格参考；开启真实透明背景）：

> Create a NEW SEPARATE transparent PNG game sprite matching the supplied reference scene's handcrafted pixel art, colors and daylight. Reference is STYLE REFERENCE only, not a landscape edit. Subject: one elegant overhanging autumn Japanese maple branch entering at UPPER LEFT from offscreen left, curving diagonally down and right, tapering into several delicate naturally forked twigs, with small individually readable 5-point / 7-point maple leaves and irregular airy clusters. Warm burnt crimson, wine red, terracotta and a few golden ochre leaves, dark warm brown angular bark with modest pixel highlights. Similar high-quality detailed pixel clusters to reference, not smooth vector, not repetitive circles or solid blobs. The entire isolated branch occupies the full width of a wide approximately 2.3:1 horizontal sprite, with sturdy cut stem at far LEFT near top, rightmost end thin delicate twigs. Composition edge-to-edge around the branch, no huge empty padding. Generous transparent gaps between leaf clusters. Absolutely no sky, mountains, water, scenery, ground, shadow backdrop, text, UI or checkerboard painted into image. True alpha transparency for all background pixels. ONLY one connected maple branch with leaves, nothing else. Keep the stem visible and plausible; compact branch, small maple leaves relative to the branch, pleasing graceful airy silhouette, polish to the reference's art quality. Do not include falling detached leaves.

岩岸（新生成；概念图仅作风格参考；开启真实透明背景）：

> Create the separate FOREGROUND ROCKS AND SHORELINE layer for the supplied pixel-art lake scene, transparent PNG, exactly matching its composition and pixel scale. Use a full 16:9 wide canvas and preserve placement of the scene's bottom corners. ONLY draw two small asymmetrical rocky banks: one rooted in BOTTOM LEFT corner, one rooted in BOTTOM RIGHT corner. All of upper 78% of image must be truly alpha transparent. Central bottom 55% of width must also remain transparent open lake (no connecting ground strip). Near grey warm-brown irregular rocks with dark cool undersides, a few tiny moss patches, dry golden brown grasses and scattered ochre maple leaf litter on the banks. Left bank can extend from x0 to27% width, right from x78% to100%; maximum height 15% of image at far corners tapering to 0 along center. Exactly match reference painterly handcrafted PIXEL ART rock edge clusters, subtle angular texture; no smooth 3D, no heavy outlines, no overly detailed random noise. Do NOT include tall reeds or cattails (those will be animated separately), no branches, no mountains, no water, no sky or backdrop, no floating leaves, no shadows onto transparent areas, no text. The output is a true alpha compositing layer, empty transparent everywhere except the low bottom-corner rock banks. No checkerboard pattern, no background scenery. Keep center open.

岩岸在0.2.0曾向下放置25逻辑像素；0.3.0按照用户参考图恢复到y=0，让底部石块完整露出，并重画水域边界。未修改生成PNG的像素或alpha，原始分辨率与透明文件保留可编辑。


## 0.3.0 新增近景密叶

新增 `public/assets/autumn_day/maple-near-canopy-v3.png`（RGBA，真正透明）。使用内置 imagegen 生成，用户提供的概念图仅作风格和构图参考。原有稀疏悬枝放大到220×100/210×94逻辑像素；近景密叶独立位于其前方，215×100/210×100，顶边裁去一部分，形成靠近镜头的包围感。水面远/近两层漂叶是程序驱动的独立叶精灵，并非贴在背景图上的绘画。

最终提示词：

> Use case: stylized-concept. Create a NEW independent transparent PNG foreground canopy sprite for this exact pixel-art autumn lakeside game. The supplied image is STYLE AND COMPOSITION REFERENCE, not an edit target. Reproduce the dense close-to-camera foliage mass visible in its UPPER LEFT CORNER as one isolated corner-canopy asset. A broad, densely overlapping mass of red, rusty orange and golden five-point/seven-point maple leaves, with angular dark brown natural branching visible in gaps. The canopy must feel very close to the viewer: larger individual leaf shapes, rich irregular density, layered clumps, many subtly different leaf orientations. Shape: leaves connect naturally to off-canvas top and left, dense upper-left core filling about the upper 60% of a wide 2.2:1 rectangle; lower and right boundary trails off into graceful sparse twig tips and individual maple leaves. NOT a single long sparse diagonal branch, NOT a row of identical leaf shapes, NOT circular leaf blobs. Matching handcrafted 16-bit/32-bit pixel art with crisp pixel clusters, warm muted autumn palette and soft clear afternoon daylight, no excessive neon saturated red, no smooth gradients. True alpha background everywhere outside foliage and between leaf gaps, no opaque backdrop. Only the canopy: no sky, mountains, lake, trees in distance, rocks, UI, text, shadow rectangle or checkerboard. The image will be composited at the upper edge, with top/left naturally cropped and central lake/sky remaining open. Preserve coherent darker shadows under the near leaves and gentle golden leaf tips, natural high-quality pixel art matching the reference.

## 两侧树冠细修

左侧沿竖向叠放原密叶素材，右侧使用内置 imagegen 单独生成的 public/assets/autumn_day/maple-right-corner-v4.png。

> Create an isolated transparent PNG sprite for the TOP RIGHT corner of the supplied pixel-art autumn lake reference. Reference is style and composition only. Compact roughly square, a dense cluster in the top RIGHT corner, cropped naturally along top AND right edges. Small dark branch enters from right; several pendant twig stems run VERTICALLY down the right side with irregular dangling maple clusters, others fan left and diagonally, with layered leaf angles, density and some gaps. Asymmetrical compact silhouette unlike the broad left canopy. Red wine, rust and sparse ochre Japanese maple leaves. Authentic square pixel clusters, subdued afternoon daylight, match the reference. Only isolated foliage on true alpha, no scenery or text.

### maple-left-v5.png

Generated with built-in imagegen.

> Create a newly painted isolated transparent PNG sprite closely matching ONLY the UPPER LEFT maple canopy composition of this reference, for a pixel art game. Do not crop the reference. Wide canvas approximately 1.85:1. Dense overlapping tiny wine-red, russet and ochre pointed maple leaves fill the upper left corner, connected across the top edge; long thin angular dark twigs extend along the top toward the right edge. A separate slender twig arcs diagonally downward from the left edge into the middle, with airy clusters and two sparse almost vertical hanging sprays along the left margin, reaching the lower border. Lower right quadrant mostly transparent. Match the reference leaf scale: many small 5–7 pointed leaves, no gigantic maple stars, no massive trunk. Desaturated warm brick red, muted gold, rich dark brown. Crisp low-resolution pixel clusters, no glow, no airbrush, no colored haze. True alpha only behind and between leaves, no sky, ground, scenery, text or checkerboard. Let foliage meet and crop at top and left edges. Paint new details following the silhouette of the reference.

### maple-right-v5.png

Generated with built-in imagegen.

> New isolated transparent pixel art sprite independently painted to closely match the UPPER RIGHT maple canopy silhouette in this reference. Use reference only as guide, no extraction. Aspect ratio about 1.45:1. Anchored and cropped into TOP and RIGHT edges, dense dark rusty-red and muted gold maple leaves in the extreme corner, slender mostly horizontal twigs reaching left near top edge, another angular slender twig curves left and down into the middle at two thirds height. A handful of narrow vertical leaf sprays at extreme right continue down to the bottom edge. Interior and bottom left mostly empty alpha. Small crisp serrated pointed leaves at the reference's scale, lots of visible gaps, no thick trunk, no huge leaf shapes, no perfectly symmetrical arrangement. Muted dark brick red, pale ochre, russet, dark woody stems. Faithful fine Japanese indie game pixel art, hard pixel clusters, no glow or smooth shading. True transparent background, no blue sky, scenery or text.

### water-maple-atlas-v5.png

Generated with built-in imagegen.

> A game asset atlas of four isolated Japanese maple leaf pixel sprites, 2 by 2 grid, one leaf centered in each quadrant. The four leaves are made of completely opaque hard-edged square pixels. Transparent negative space all the way up to the sharp pixel edge, including gaps between the lobes. Classic 16-bit pixel graphics, each leaf about 35 pixels wide and 12 pixels high at its virtual pixel resolution, enlarged with nearest-neighbor. Viewed at a low angle, each leaf flat and wide, crisp maple shape with five pointed serrated lobes and a small stem. Four varied silhouettes, dark brick red, burnt orange, red ochre, chestnut. Flat limited color palette of four shades per leaf, small hard-edged highlights, no smooth transitions. The sprites are simple flat objects, unlit, with no glow, bloom, colored haze, contact shadow, scenery or lettering. Spacious gutters, pure transparent alpha.

### maple-left-short-twig-v6.png

Built-in imagegen.

> Edit first image, the transparent left canopy game asset. Keep its top crown and main branches. Remove the two long thin vertical maple sprays hanging down at far left below the diagonal branch. Replace them with ONE short twig coming from left, slanting down and RIGHT at approximately 45 degrees, with a few separated groups of red and one ochre maple leaf, just like the diagonal twig in the second screenshot, which is a style and silhouette reference only. End twig well above bottom of original canvas, with wide transparent gaps. Preserve original top and left crop, canvas proportions, pixel art and transparent alpha. No sky or scenery, no glow.
