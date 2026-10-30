import {Extension} from '@tiptap/core';
import {Plugin,PluginKey} from '@tiptap/pm/state';
import {Step,StepResult,StepMap} from '@tiptap/pm/transform';

export const documentFontKey=new PluginKey('workmoireDocumentFont');
export const BODY_FONT_VALUES=['system','sans','serif','inter','mono'];
export const validBodyFont=value=>BODY_FONT_VALUES.includes(value)?value:'sans';
// Keep font history separate from document markup: changing the root's attributes
// makes ProseMirror rebuild all node views, including an open PDF iframe.
export class DocumentFontStep extends Step {
 constructor(value,previous){super();this.value=validBodyFont(value);this.previous=validBodyFont(previous);}
 apply(doc){return StepResult.ok(doc);}
 getMap(){return StepMap.empty;}
 invert(){return new DocumentFontStep(this.previous,this.value);}
 map(){return this;}
 toJSON(){return {stepType:'workmoireDocumentFont',value:this.value,previous:this.previous};}
 static fromJSON(schema,json){return new DocumentFontStep(json.value,json.previous);}
}
Step.jsonID('workmoireDocumentFont',DocumentFontStep);
export function documentFontExtension(initial){
 return Extension.create({name:'documentFont',addProseMirrorPlugins(){return [new Plugin({key:documentFontKey,state:{init:()=>validBodyFont(initial),apply(tr,value){for(const step of tr.steps)if(step instanceof DocumentFontStep)value=step.value;return value;}}})];}});
}
