// server/api/facilitator.ts

import { readBody, eventHandler } from 'h3'
import { Connection } from '@solana/web3.js'
import base64js from 'base64-js'

const SOLANA_RPC_URL = 'https://api.devnet.solana.com'

export const config = {
    runtime: 'nodejs',
}

export default eventHandler(async (event) => {
    try {
        console.log('FACILITATOR: 📥 Incoming facilitator request...')

        const {
            signedTransactionB64,
            expectedRecipient,
            expectedAmountLamports,
        } = await readBody(event)

        console.log('FACILITATOR: 🔍 Payload received:', {
            expectedRecipient,
            expectedAmountLamports,
            signedTransactionB64: signedTransactionB64?.slice(0, 24) + '...', // abbreviated
        })

        if (!signedTransactionB64 || !expectedRecipient || !expectedAmountLamports) {
            console.warn('FACILITATOR: ⚠️ Missing required fields in request')
            return { allowed: false, error: 'Missing required fields' }
        }

        const connection = new Connection(SOLANA_RPC_URL, 'confirmed')

        // Decode and send transaction
        const txBytes = base64js.toByteArray(signedTransactionB64)

        console.log('FACILITATOR: 🚀 Sending raw transaction to Solana...')
        const txid = await connection.sendRawTransaction(txBytes, {
            skipPreflight: false,
            preflightCommitment: 'confirmed',
        })

        console.log('FACILITATOR: ⏳ Waiting for confirmation...')
        const latest = await connection.getLatestBlockhash('finalized')
        await connection.confirmTransaction(
            {
                signature: txid,
                blockhash: latest.blockhash,
                lastValidBlockHeight: latest.lastValidBlockHeight,
            },
            'confirmed',
        )

        console.log('FACILITATOR: 🔎 Fetching and parsing transaction...')
        const parsed = await connection.getParsedTransaction(txid, {
            maxSupportedTransactionVersion: 0,
        })

        if (!parsed || !parsed.transaction?.message?.instructions?.length) {
            console.error('FACILITATOR: ❌ Could not parse transaction or no instructions found')
            return { allowed: false, error: 'Could not parse transaction' }
        }

        const expectedLamports = BigInt(expectedAmountLamports)

        const validTransfer = parsed.transaction.message.instructions.some((ix: any) => {
            if (
                ix.program !== 'system'
                || ix.parsed?.type !== 'transfer'
            ) return false

            const recipientPubkey = ix.parsed.info.destination
            const lamports = BigInt(ix.parsed.info.lamports)

            console.log('FACILITATOR: 🔬 Inspecting transfer instruction:', {
                recipientPubkey,
                lamports,
                expectedRecipient,
                expectedLamports,
            })

            return (
                recipientPubkey === expectedRecipient
                && lamports === expectedLamports
            )
        })

        if (!validTransfer) {
            console.warn('FACILITATOR: ⚠️ Transaction found, but transfer does not match expected values')
            return { allowed: false, error: 'Transfer mismatch or invalid format' }
        }

        console.log('✅ Transaction valid and confirmed:', txid)

        return {
            allowed: true,
            txid,
        }
    }
    catch (err: any) {
        console.error('❌ Facilitator error:', err)
        return {
            allowed: false,
            error: err.message || 'Internal Server Error',
        }
    }
})
