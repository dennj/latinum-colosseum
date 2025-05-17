// server/api/balance.ts

/*
curl -X POST http://localhost:3000/api/check_balance \
  -H "Content-Type: application/json" \
  -d '{"publicKey": "3BMEwjrn9gBfSetARPrAK1nPTXMRsvQzZLN1n4CYjpcU"}'
{
  "publicKey": "3BMEwjrn9gBfSetARPrAK1nPTXMRsvQzZLN1n4CYjpcU",
  "balanceLamports": 3999995411,
  "balanceSol": 3.999995411
}
*/

import { readBody } from 'h3'
import { Connection, PublicKey } from '@solana/web3.js'

const SOLANA_RPC_URL = 'https://api.devnet.solana.com'

export default defineEventHandler(async (event) => {
    const body = await readBody(event)
    const publicKeyStr = body?.publicKey

    if (!publicKeyStr) {
        throw createError({
            statusCode: 400,
            statusMessage: 'Missing publicKey in request body',
        })
    }

    try {
        const publicKey = new PublicKey(publicKeyStr)
        const connection = new Connection(SOLANA_RPC_URL, 'confirmed')

        const balanceLamports = await connection.getBalance(publicKey)
        const balanceSol = balanceLamports / 1_000_000_000

        return {
            publicKey: publicKeyStr,
            balanceLamports,
            balanceSol,
        }
    }
    catch (err: any) {
        throw createError({
            statusCode: 400,
            statusMessage: `Invalid public key or network issue: ${err.message}`,
        })
    }
})
