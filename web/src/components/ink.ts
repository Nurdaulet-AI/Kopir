/** Тёмный или белый текст — по яркости цвета маячка (жёлтый и белый текст не читаются). */
export function beaconInk(hex: string | undefined): string {
  if (!hex) return "#fff";
  const [r, g, b] = [1, 3, 5].map((i) => {
    const c = parseInt(hex.slice(i, i + 2), 16) / 255;
    return c <= 0.04045 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4;
  });
  return 0.2126 * r + 0.7152 * g + 0.0722 * b > 0.3 ? "#10161d" : "#fff";
}
