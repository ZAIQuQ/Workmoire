import {
  createElement, FileText, BookOpen, Network, Search, Keyboard, Menu, Upload,
  Underline, Strikethrough, Highlighter, ListOrdered, AlignLeft, AlignCenter, AlignRight,
  GripVertical, ArrowUp, ArrowDown, Copy, IndentIncrease, IndentDecrease, Subscript, Superscript, Eraser,
  ArrowUpRight, ArrowLeft, Link, Image, Trash2, Clock3, PanelRight,
  Maximize2, Check, Plus, X, Bold, Italic, Code, ListTodo, List, Quote, Sigma,
  Variable, Table2, Omega, Minus, Undo2, Redo2, Pin, ChevronDown, ChevronLeft,
  ChevronRight, Ellipsis, FilePenLine, Lightbulb, Route, ClipboardCheck,
  Columns2, Eye, Download, Hash, NotebookPen, LockKeyhole, ArrowRight
} from "lucide";

// Named imports keep this bundle limited to the icons actually used by the notebook.
const icons = {
  underline:Underline, strike:Strikethrough, highlight:Highlighter, ordered:ListOrdered,
  "align-left":AlignLeft, "align-center":AlignCenter, "align-right":AlignRight,
  grip:GripVertical, up:ArrowUp, down:ArrowDown, copy:Copy, indent:IndentIncrease, outdent:IndentDecrease,
  subscript:Subscript, superscript:Superscript, clear:Eraser,
  document:FileText, book:BookOpen, relations:Network, search:Search,
  keyboard:Keyboard, menu:Menu, upload:Upload, arrow:ArrowUpRight,
  back:ArrowLeft, link:Link, image:Image, trash:Trash2, clock:Clock3,
  spark:NotebookPen, panel:PanelRight, expand:Maximize2, check:Check,
  plus:Plus, close:X, bold:Bold, italic:Italic, code:Code, task:ListTodo,
  list:List, quote:Quote, formula:Sigma, variable:Variable, table:Table2,
  symbols:Omega, minus:Minus, undo:Undo2, redo:Redo2, pin:Pin,
  chevron:ChevronDown, previous:ChevronLeft, next:ChevronRight,
  more:Ellipsis, write:FilePenLine, idea:Lightbulb, plan:Route,
  review:ClipboardCheck, split:Columns2, read:Eye, download:Download,
  tag:Hash, notebook:NotebookPen, lock:LockKeyhole, forward:ArrowRight
};
function render(name,extraClass="") {
  return createElement(icons[name]||FileText,{
    class:"icon"+(extraClass?" "+extraClass:""),width:20,height:20,
    "stroke-width":1.75,"aria-hidden":"true",focusable:"false"
  }).outerHTML;
}
window.WorkmoireIcons={render};
document.querySelectorAll("[data-icon]").forEach(node=>{node.innerHTML=render(node.dataset.icon);});
