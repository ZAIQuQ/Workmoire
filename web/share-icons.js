import {createElement,FileText,BookOpen,Copy,ChevronDown,ChevronLeft,ChevronRight,ArrowUpRight,Sun,Moon,Search,Download,X,LockKeyhole} from 'lucide';
const icons={document:FileText,book:BookOpen,copy:Copy,chevron:ChevronDown,previous:ChevronLeft,next:ChevronRight,arrow:ArrowUpRight,sun:Sun,moon:Moon,search:Search,download:Download,close:X,lock:LockKeyhole};
const render=name=>createElement(icons[name]||FileText,{class:'icon',width:18,height:18,'stroke-width':1.75,'aria-hidden':'true'}).outerHTML;
window.WorkmoireIcons={render};document.querySelectorAll('[data-icon]').forEach(el=>el.innerHTML=render(el.dataset.icon));
