
import 'dotenv/config';
import { BlobServiceClient } from '@azure/storage-blob';
import { promises as fs } from 'fs';

const conn = process.env.AZURE_STORAGE_CONNECTION_STRING;
const container = process.env.AZURE_BLOB_CONTAINER;

export async function writeJson(path: string, data: unknown) {
  const body = typeof data === 'string' ? Buffer.from(data, 'utf-8') : Buffer.from(JSON.stringify(data, null, 2), 'utf-8');
  if (conn && container) {
    const client = BlobServiceClient.fromConnectionString(conn);
    const blob = client.getContainerClient(container).getBlockBlobClient(path);
    await blob.uploadData(body, { blobHTTPHeaders: { blobContentType: guessContentType(path) } });
    console.log(`Uploaded to blob: ${path}`);
  } else {
    await fs.mkdir('out', { recursive: true });
    const safe = path.replace(/\//g, '_');
    await fs.writeFile(`out/${safe}`, body);
    console.log(`Wrote local file: out/${safe}`);
  }
}

function guessContentType(path: string): string {
  if (path.endsWith('.csv')) return 'text/csv';
  return 'application/json';
}
