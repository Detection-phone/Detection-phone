export async function handleDownloadImage(filename: string): Promise<void> {
  if (!filename) throw new Error('Missing filename');

  const imageUrl = `http://localhost:5000/detections/${encodeURIComponent(filename)}`;

  const res = await fetch(imageUrl, { credentials: 'include' });
  if (!res.ok) {
    const message = `Failed to download (status ${res.status})`;
    throw new Error(message);
  }

  const blob = await res.blob();
  const objectUrl = URL.createObjectURL(blob);
  try {
    const link = document.createElement('a');
    link.href = objectUrl;
    link.setAttribute('download', filename);
    link.style.display = 'none';
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  } finally {
    URL.revokeObjectURL(objectUrl);
  }
}


