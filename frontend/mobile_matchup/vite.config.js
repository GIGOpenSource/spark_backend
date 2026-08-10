import { defineConfig } from 'vite'
import uni from '@dcloudio/vite-plugin-uni'
import path from 'path'
import fs from 'fs'

export default defineConfig({
  plugins: [
    uni(),
    {
      name: 'matchup-favicon',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === '/favicon.ico') {
            const file = path.resolve(__dirname, 'static/tab/discover-active.png')
            res.setHeader('Content-Type', 'image/png')
            fs.createReadStream(file).pipe(res)
            return
          }
          next()
        })
      }
    }
  ],
  transpileDependencies: ['uview-plus', 'lime-painter'],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './'),
      // uni easycom autoscan emits bare "components/..." imports; Vite needs this alias
      components: path.resolve(__dirname, 'components'),
    }
  }
})
