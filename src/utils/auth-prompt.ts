
import * as readline from 'readline';

export interface Credentials {
  username: string;
  password: string;
  totpSecret?: string;
  mfaMode?: 'TOTP' | 'PUSH';
}

/**
 * Prompts user for credentials interactively via console
 */
export async function promptForCredentials(): Promise<Credentials> {
  const rl = readline.createInterface({
    input: process.stdin,
    output: process.stdout,
  });

  const question = (prompt: string): Promise<string> => {
    return new Promise(resolve => {
      rl.question(prompt, resolve);
    });
  };

  console.log('\n=== Entra ID Authentication Setup ===');
  console.log('Please provide your credentials to authenticate with the intranet site.\n');

  const username = await question('Username (email): ');
  const password = await question('Password: ');
  const mfaChoice = await question('MFA Mode (1=TOTP/Authenticator App, 2=PUSH/Approve on device) [1]: ');
  
  const mfaMode = mfaChoice.trim() === '2' ? 'PUSH' : 'TOTP';
  let totpSecret: string | undefined;

  if (mfaMode === 'TOTP') {
    totpSecret = await question('TOTP Secret (Base32, from authenticator app): ');
  }

  rl.close();

  return {
    username: username.trim(),
    password: password.trim(),
    mfaMode,
    totpSecret: totpSecret?.trim(),
  };
}

/**
 * Check if stored authentication state exists
 */
export function hasStoredAuth(): boolean {
  try {
    const fs = require('fs');
    return fs.existsSync('auth.json');
  } catch {
    return false;
  }
}
