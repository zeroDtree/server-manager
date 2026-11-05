// Mermaid imports `elkjs/lib/elk.bundled.js` as a default ESM export. The file is
// Browserify CJS; Vite dev needs an explicit default re-export.
import * as elkModule from '../node_modules/elkjs/lib/elk.bundled.js'

const ELK = elkModule.default ?? elkModule

export default ELK
