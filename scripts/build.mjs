import {build} from "esbuild";
import {cp,mkdir,readFile,writeFile} from "node:fs/promises";
await mkdir("workspace/static/vendor",{recursive:true});
await build({entryPoints:["web/editor-vendor.js"],bundle:true,minify:true,target:["es2022"],outfile:"workspace/static/vendor/editor.js",legalComments:"eof"});
await build({entryPoints:["web/pdf-viewer.js"],bundle:true,minify:true,format:"esm",target:["es2022"],outfile:"workspace/static/vendor/pdf-reader.mjs",legalComments:"eof"});
for(const [source,destination] of [["build/pdf.worker.min.mjs","pdf.worker.min.mjs"],["web/pdf_viewer.css","pdf-viewer.css"],["cmaps","pdf-cmaps"],["standard_fonts","pdf-fonts"],["wasm","pdf-wasm"],["web/images","images"]])await cp("node_modules/pdfjs-dist/"+source,"workspace/static/vendor/"+destination,{recursive:true});
await cp("node_modules/katex/dist/katex.min.css","workspace/static/vendor/katex.min.css");
await cp("node_modules/katex/dist/fonts","workspace/static/vendor/fonts",{recursive:true});
const licenses=[];
for(const [name,version] of Object.entries(JSON.parse(await readFile("package.json","utf8")).dependencies)){
  let license="";
  for(const filename of ["LICENSE","LICENSE.md","LICENSE.txt"]){try{license=await readFile("node_modules/"+name+"/"+filename,"utf8");break;}catch{}}
  licenses.push(name+" "+version+"\n"+license);
}
await writeFile("workspace/static/vendor/THIRD_PARTY_LICENSES.txt",licenses.join("\n\n---\n\n"));
