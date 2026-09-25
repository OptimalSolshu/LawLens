// Mongolian vowel harmony of the last spoken number word decides the suffix:
// нэг (1), дөрөв (4), ес (9), дөч (40), ер (90) take front forms (дүгээр, дэх).
function isFront(n: number): boolean {
  if (n % 10 !== 0) return [1, 4, 9].includes(n % 10);
  if (n % 100 !== 0) return [4, 9].includes((n % 100) / 10);
  return false; // зуу, мянга
}

/** "15" -> "15 дугаар зүйл", "33.2" -> "33.2 дахь хэсэг", "15.1.3" -> "15.1.3 дахь заалт". */
export function provisionLabel(number: string): string {
  const parts = number.split(".");
  const last = Number(parts[parts.length - 1]);
  const front = Number.isFinite(last) && isFront(last);
  if (parts.length === 1) return `${number} ${front ? "дүгээр" : "дугаар"} зүйл`;
  return `${number} ${front ? "дэх" : "дахь"} ${parts.length === 2 ? "хэсэг" : "заалт"}`;
}
