import { access, cp, mkdir, readFile, rm, writeFile } from 'node:fs/promises'
import path from 'node:path'
import process from 'node:process'
import { fileURLToPath } from 'node:url'

const scriptDir = fileURLToPath(new URL('.', import.meta.url))
const frontendRoot = path.resolve(scriptDir, '..')
const supportedBuilds = new Set(['web-mobile', 'web-desktop'])
const selectedBuild = process.argv[2] || 'web-mobile'

if (!supportedBuilds.has(selectedBuild)) {
  console.error(`[sync-scgame] unsupported build target: ${selectedBuild}`)
  console.error('[sync-scgame] expected one of: web-mobile, web-desktop')
  process.exit(1)
}

const sourceDir = path.resolve(frontendRoot, '..', 'SCgame-dev', 'build', selectedBuild)
const targetDir = path.resolve(frontendRoot, 'public', 'scgame')
const targetIndexPath = path.join(targetDir, 'index.html')

const readOptionalFile = async (filePath) => {
  try {
    return await readFile(filePath, 'utf8')
  } catch {
    return null
  }
}

try {
  await access(sourceDir)
} catch {
  console.error(`[sync-scgame] build folder not found: ${sourceDir}`)
  process.exit(1)
}

const customIndexHtml = await readOptionalFile(targetIndexPath)

await rm(targetDir, { recursive: true, force: true })
await mkdir(path.dirname(targetDir), { recursive: true })
await cp(sourceDir, targetDir, { recursive: true })

if (customIndexHtml !== null) {
  await writeFile(targetIndexPath, customIndexHtml, 'utf8')
}

console.log(`[sync-scgame] synced ${selectedBuild} -> ${path.relative(frontendRoot, targetDir)}`)

if (customIndexHtml !== null) {
  console.log('[sync-scgame] restored custom public/scgame/index.html')
}
