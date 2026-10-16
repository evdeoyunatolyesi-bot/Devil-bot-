# DEVIL CHATS — Python + Vercel demo

## Deploy to Vercel
1. Upload/extract this folder into a GitHub repository.
2. Import the repository into Vercel.
3. In Vercel Project Settings → Environment Variables, add:
   - `ROOM_SECRET` = a long random secret (do not commit it to GitHub).
4. Deploy.

Files:
- `api/index.py`: Python serverless API
- `public/index.html`: website UI and browser code
- `vercel.json`: Vercel routes/build configuration
- `requirements.txt`: dependencies (uses Python standard library)

## Important limitations
This is a demo, not production-grade private messaging. Vercel serverless functions are stateless/ephemeral: this code's in-memory room/message store may not be shared across function invocations or instances, so messages may fail to sync consistently. For a real deployed chat, use a persistent/shared store (e.g. Vercel Postgres/Redis/KV or another database) and a realtime service such as Ably/Pusher/Supabase Realtime. Add rate limiting, abuse controls, and secure room authentication.

The shared passphrase alone identifies a room; usernames can differ. Anyone who knows the passphrase can potentially access that room. This demo does not implement end-to-end encryption, so don't send sensitive information. Use HTTPS and a strong `ROOM_SECRET` in deployment.
