export function formatFileSize(bytes: number): string {
  if (!Number.isFinite(bytes) || bytes < 0) throw new RangeError('Invalid file size');
  if (bytes === 0) return '0 Bytes';
  const units = ['Bytes', 'KB', 'MB', 'GB'];
  const index = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1);
  return `${Math.round(bytes / 1024 ** index)} ${units[index]}`;
}
