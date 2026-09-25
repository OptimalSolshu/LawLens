export function Loading() {
  return (
    <p role="status" className="py-3 text-ink-2">
      Ачаалж байна…
    </p>
  );
}

export function Empty({ children = "Холбоотой заалт олдсонгүй." }: { children?: string }) {
  return <p className="py-3 text-ink-2">{children}</p>;
}

export function ErrorState({ onRetry }: { onRetry: () => void }) {
  return (
    <p role="alert" className="py-3 text-warn">
      Мэдээлэл ачаалахад алдаа гарлаа.{" "}
      <button type="button" onClick={onRetry} className="text-accent underline">
        Дахин оролдох
      </button>
    </p>
  );
}
