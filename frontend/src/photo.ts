// Prepares a phone photo of a paper form before it is read.
// The same upright, resized image is sent to the reader and shown on the guided-fill screen,
// so the box positions the reader returns line up with what the person sees.

const MAX_SIDE = 2000;

export interface Photo {
  blob: Blob;
  url: string;
}

async function decode(file: File): Promise<CanvasImageSource & { width: number; height: number }> {
  try {
    // applies the camera's rotation (EXIF), so a sideways phone photo comes out upright
    return await createImageBitmap(file, { imageOrientation: "from-image" });
  } catch {
    const url = URL.createObjectURL(file);
    try {
      const img = new Image();
      img.src = url;
      await img.decode();
      return Object.assign(img, { width: img.naturalWidth, height: img.naturalHeight });
    } finally {
      URL.revokeObjectURL(url);
    }
  }
}

export async function preparePhoto(file: File): Promise<Photo> {
  const img = await decode(file);
  const scale = Math.min(1, MAX_SIDE / Math.max(img.width, img.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(img.width * scale);
  canvas.height = Math.round(img.height * scale);
  canvas.getContext("2d")!.drawImage(img, 0, 0, canvas.width, canvas.height);
  const blob = await new Promise<Blob>((resolve, reject) =>
    canvas.toBlob((b) => (b ? resolve(b) : reject(new Error("encode"))), "image/jpeg", 0.88),
  );
  return { blob, url: URL.createObjectURL(blob) };
}
