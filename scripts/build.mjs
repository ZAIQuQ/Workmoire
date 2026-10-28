import {build} from "esbuild";
import {gzipSync} from "node:zlib";
import {cp,mkdir,readFile,writeFile,rm} from "node:fs/promises";
await mkdir("workspace/static/vendor",{recursive:true});
await build({entryPoints:["web/interface-assets.js"],bundle:true,minify:true,target:["es2022"],outfile:"workspace/static/vendor/interface.js",legalComments:"eof"});
await build({entryPoints:["web/editor-vendor.js"],bundle:true,minify:true,supported:{"template-literal":false},target:["es2022"],outfile:"workspace/static/vendor/editor.js",legalComments:"eof"});
await build({entryPoints:["web/pdf-viewer.js"],bundle:true,minify:true,format:"esm",target:["es2022"],outfile:"workspace/static/vendor/pdf-reader.mjs",legalComments:"eof"});
await build({entryPoints:["web/pdf-extractor.js"],bundle:true,minify:true,format:"esm",target:["es2022"],outfile:"workspace/static/vendor/pdf-extractor.mjs",legalComments:"eof"});
await build({entryPoints:["web/share-icons.js"],bundle:true,minify:true,target:["es2022"],outfile:"workspace/static/vendor/share-icons.js",legalComments:"eof"});
await build({entryPoints:["web/share-reader.js"],bundle:true,minify:true,target:["es2022"],outfile:"workspace/static/vendor/share-reader.js",legalComments:"eof"});
for(const [source,destination] of [["build/pdf.worker.min.mjs","pdf.worker.min.mjs"],["web/pdf_viewer.css","pdf-viewer.css"],["cmaps","pdf-cmaps"],["standard_fonts","pdf-fonts"],["wasm","pdf-wasm"],["web/images","images"]])await cp("node_modules/pdfjs-dist/"+source,"workspace/static/vendor/"+destination,{recursive:true});
await cp("node_modules/katex/dist/katex.min.css","workspace/static/vendor/katex.min.css");
await cp("node_modules/katex/dist/fonts","workspace/static/vendor/fonts",{recursive:true});
// Fontsource's Unicode ranges load only the character subsets needed on a page.
let typeCSS="";
await rm("workspace/static/vendor/type",{recursive:true,force:true});
await mkdir("workspace/static/vendor/type",{recursive:true});
for(const family of ["inter","noto-sans-sc","noto-serif-sc"]){
  const root="node_modules/@fontsource-variable/"+family;
  const css=await readFile(root+"/index.css","utf8");
  const files=[...css.matchAll(/url\(\.\/files\/([^)]*)\)/g)].map(match=>match[1]);
  for(const file of files)await cp(root+"/files/"+file,"workspace/static/vendor/type/"+file);
  typeCSS+=css.replaceAll("./files/","./type/")+"\n";
}
await writeFile("workspace/static/vendor/type.css",typeCSS);
const licenses=[];
const lock=JSON.parse(await readFile("package-lock.json","utf8"));
for(const [path,entry] of Object.entries(lock.packages)){
  if(!path||entry.dev||entry.optional&&entry.os)continue;
  let metadata;
  try{metadata=JSON.parse(await readFile(path+"/package.json","utf8"));}catch{continue;}
  let license="";
  for(const filename of ["LICENSE","LICENSE.md","LICENSE.txt","LICENSE-MIT","LICENSE-MIT.txt","license","license.md","license.txt","COPYING"]){try{license=await readFile(path+"/"+filename,"utf8");break;}catch{}}
  if(!license)throw new Error("Missing runtime license notice: "+metadata.name);
  licenses.push(metadata.name+" "+metadata.version+"\n"+license);
}
await writeFile("workspace/static/vendor/THIRD_PARTY_LICENSES.txt",licenses.join("\n\n---\n\n"));
// Precompress public text assets; the server negotiates gzip and detects stale copies.
for(const name of ["editor-toolbar.css","document-outline.css","share.html","share.css","share-pdf-viewer.html","vendor/share-icons.js","vendor/share-reader.js","index.html","app.js","app.css","design-tokens.css","rich-editor.css","code-block.css","organization.css","pdf-viewer.html","pdf-viewer.css","vendor/editor.js","vendor/interface.js","vendor/pdf-reader.mjs","vendor/pdf-extractor.mjs","vendor/pdf.worker.min.mjs","vendor/type.css","vendor/pdf-viewer.css","vendor/katex.min.css"]){
  const raw=await readFile("workspace/static/"+name);
  await writeFile("workspace/static/"+name+".gz",gzipSync(raw,{level:9}));
}
