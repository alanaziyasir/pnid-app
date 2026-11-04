import { describe, expect, it } from 'vitest';
import { formatFileSize } from './format';

describe('upload file size display', () => {
  it.each([
    [0, '0 Bytes'],
    [1, '1 Bytes'],
    [1024, '1 KB'],
    [1536, '2 KB'],
    [50 * 1024 ** 2, '50 MB'],
    [1024 ** 4, '1024 GB'],
  ])('formats %s bytes as %s', (bytes, expected) => expect(formatFileSize(bytes)).toBe(expected));
  it.each([-1, NaN, Infinity])('rejects invalid sizes: %s', (bytes) => {
    expect(() => formatFileSize(bytes)).toThrow(RangeError);
  });
});
