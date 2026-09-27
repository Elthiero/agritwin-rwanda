/**
 * The hero illustration is the product's own chart, drawn as landscape: Rwanda's
 * terraced hillsides standing in for the yield-gap curve (attainable above,
 * actual below, the gap between them), in the same viridis ramp the map legend
 * uses. Not decoration — the metaphor is the content.
 */
const POINTS_X = [40, 190, 340, 490, 600]
const ATTAINABLE_Y = [92, 72, 86, 60, 78]
const ACTUAL_Y = [148, 138, 154, 104, 140]

function smoothPath(xs: number[], ys: number[]): string {
  let d = `M${xs[0]},${ys[0]}`
  for (let i = 1; i < xs.length; i++) {
    const cx = (xs[i - 1] + xs[i]) / 2
    d += ` C${cx},${ys[i - 1]} ${cx},${ys[i]} ${xs[i]},${ys[i]}`
  }
  return d
}

export default function HeroTerraces() {
  const attainablePath = smoothPath(POINTS_X, ATTAINABLE_Y)
  const actualPath = smoothPath(POINTS_X, ACTUAL_Y)

  return (
    <svg
      className="hero-art"
      viewBox="0 0 640 460"
      role="img"
      aria-label="Illustration: attainable yield traced above actual yield across five districts, the gap between them shaded, over terraced hillsides."
    >
      <circle cx="600" cy="34" r="24" fill="var(--harvest-soft)" opacity="0.7" />

      {/* gap whiskers, drawn first so the lines sit on top */}
      {POINTS_X.map((x, i) => (
        <line
          key={x}
          x1={x}
          y1={ATTAINABLE_Y[i]}
          x2={x}
          y2={ACTUAL_Y[i]}
          stroke="var(--forest)"
          strokeWidth="1"
          strokeDasharray="1 4"
          opacity="0.45"
        />
      ))}

      <path
        d={attainablePath}
        fill="none"
        stroke="var(--harvest)"
        strokeWidth="2.5"
        strokeDasharray="7 6"
        strokeLinecap="round"
      />
      <path d={actualPath} fill="none" stroke="var(--forest-dark)" strokeWidth="3" strokeLinecap="round" />

      {POINTS_X.map((x, i) => (
        <g key={`markers-${x}`}>
          <circle cx={x} cy={ATTAINABLE_Y[i]} r="4" fill="var(--paper-raised)" stroke="var(--harvest)" strokeWidth="2" />
          <circle cx={x} cy={ACTUAL_Y[i]} r="4" fill="var(--forest-dark)" />
        </g>
      ))}

      {/* terraced hillsides: farthest (lightest) to nearest (darkest) */}
      <path
        d="M0,200 C80,168 160,214 240,192 C320,168 400,208 480,184 C560,158 600,192 640,176 L640,460 L0,460 Z"
        fill="#cfe0c9"
      />
      <path
        d="M0,258 C90,222 170,268 260,240 C340,212 420,258 500,230 C570,206 610,238 640,224 L640,460 L0,460 Z"
        fill="#8fbf94"
      />
      <path
        d="M0,326 C100,290 190,336 280,308 C360,284 440,320 520,298 C580,278 615,302 640,292 L640,460 L0,460 Z"
        fill="#3f8a6e"
      />
      <path
        d="M0,398 C110,364 200,402 300,378 C380,358 460,392 540,372 C590,358 620,378 640,368 L640,460 L0,460 Z"
        fill="var(--forest-dark)"
      />

      {/* terrace contour lines on the nearest ridge, echoing real hillside terracing */}
      {[412, 424, 436].map((y) => (
        <path
          key={y}
          d={`M0,${y} C110,${y - 30} 200,${y + 4} 300,${y - 16} C380,${y - 32} 460,${y - 4} 540,${y - 20} C590,${y - 32} 620,${y - 16} 640,${y - 24}`}
          fill="none"
          stroke="var(--forest)"
          strokeOpacity="0.35"
          strokeWidth="1"
        />
      ))}
    </svg>
  )
}
