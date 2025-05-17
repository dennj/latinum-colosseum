// server/api/402wallet.ts

/*
Test with:
curl -X POST http://localhost:3000/api/402wallet \
  -H "Content-Type: application/json" \
  -d '{
    "targetWallet": "3BMEwjrn9gBfSetARPrAK1nPTXMRsvQzZLN1n4CYjpcU",
    "amountLamports": 23
  }'
*/

import { readBody, eventHandler } from 'h3'
import {
    Connection,
    Keypair,
    PublicKey,
    SystemProgram,
    Transaction,
} from '@solana/web3.js'
import bs58 from 'bs58'
import base64js from 'base64-js'

const SOLANA_RPC_URL = 'https://api.devnet.solana.com'

// 🔐 Replace with your wallet's private key (base58-encoded 64-byte key)
const PRIVATE_KEY_BASE58 = 'TODO: put this somewhere safe'

// Decode base58 private key
const payer = Keypair.fromSecretKey(Uint8Array.from(bs58.decode(PRIVATE_KEY_BASE58)))

export default eventHandler(async (event) => {
    try {
        console.log('WALLET: 📥 Received 402 signing request...')

        const { amountLamports, targetWallet } = await readBody(event)

        console.log('WALLET: 🔍 Inputs:', {
            amountLamports,
            targetWallet,
        })

        if (
            !amountLamports
            || !targetWallet
            || typeof targetWallet !== 'string'
            || targetWallet.length < 32
        ) {
            console.warn('WALLET: ⚠️ Invalid request input')
            return {
                success: false,
                error: 'Missing or invalid targetWallet or amountLamports',
            }
        }

        const connection = new Connection(SOLANA_RPC_URL, 'confirmed')
        const recipient = new PublicKey(targetWallet)

        // Get recent blockhash
        const { blockhash, lastValidBlockHeight } = await connection.getLatestBlockhash('finalized')

        console.log('WALLET: 🛠️ Building and signing transaction...')

        // Build unsigned transaction
        const transaction = new Transaction({
            feePayer: payer.publicKey,
            blockhash,
            lastValidBlockHeight,
        }).add(
            SystemProgram.transfer({
                fromPubkey: payer.publicKey,
                toPubkey: recipient,
                lamports: Number(amountLamports),
            }),
        )

        // Sign transaction
        transaction.sign(payer)

        // Serialize and encode to base64
        const rawTx = transaction.serialize()
        const signedTransactionB64 = base64js.fromByteArray(rawTx)

        console.log('WALLET: ✅ Transaction signed and encoded')
        console.log(`WALLET: 📦 b64Payload: ${signedTransactionB64}`)

        return {
            success: true,
            signedTransactionB64,
            from: payer.publicKey.toBase58(),
            to: targetWallet,
            amountLamports,
            message: `${signedTransactionB64}`,
        }
    }
    catch (err: any) {
        console.error('❌ Signing Error:', err)
        return {
            success: false,
            error: err.message || 'Unknown error',
        }
    }
})
