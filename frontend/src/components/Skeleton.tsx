interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  className?: string
}

export function Skeleton({ className, ...props }: SkeletonProps) {
  return <div className={`animate-pulse rounded-md bg-surface-border ${className || ""}`} {...props} />
}
