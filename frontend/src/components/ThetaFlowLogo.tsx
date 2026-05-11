export function ThetaFlowLogo({ size = 32 }: { size?: number }) {
  const id = `tf-grad-${size}`
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 72 72"
      xmlns="http://www.w3.org/2000/svg"
      style={{ flexShrink: 0 }}
    >
      <defs>
        <linearGradient id={id} x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1f6feb" />
          <stop offset="100%" stopColor="#3fb950" />
        </linearGradient>
      </defs>
      <rect width="72" height="72" rx="18" fill={`url(#${id})`} />
      <ellipse cx="36" cy="36" rx="18" ry="22" fill="none" stroke="white" strokeWidth="3.5" />
      <path
        d="M18,36 C22,29 26,43 30,36 C34,29 38,43 42,36 C46,29 50,43 54,36"
        fill="none"
        stroke="white"
        strokeWidth="3"
        strokeLinecap="round"
      />
    </svg>
  )
}
