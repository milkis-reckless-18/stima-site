/* Tailwind for the Prova pages: the theme from Marianna's pages (tailwind.config in her <head>),
   compiled once instead of the Play CDN. Build: see tools/prova_import.py. */
module.exports = {
  content: ["./index.html", "./hiring-teams.html", "./higher-ed.html", "./prova.js"],
  theme: { extend: {
    colors: { plum:'#2A103A', coral:'#FF5B6E', mango:'#FFB238', aqua:'#11C5BF', cream:'#FFF7ED', leaf:'#6CC36C', lilac:'#C9B6E4', muted:'#6B6072', divider:'#E8DDD5' },
    fontFamily: { serif:['"DM Serif Display"','Georgia','serif'], sans:['Inter','Arial','sans-serif'] },
    boxShadow: { card:'0 8px 28px rgba(42,16,58,.08)', float:'0 18px 50px rgba(42,16,58,.16)' },
    borderRadius: { sm2:'10px', md2:'16px', lg2:'24px' },
  }},
};
