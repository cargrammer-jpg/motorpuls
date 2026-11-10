<?xml version="1.0" encoding="UTF-8"?>
<!-- Visar RSS-flödena (/feed.xml och /feed/*.xml) som en läsbar sida i webbläsaren. Flödena länkar hit med
     <?xml-stylesheet type="text/xsl" href="/feed.xsl"?> (rss() i build.py). XSLT 1.0, inga externa anrop: typsnitt och
     logga från sajten själv. RSS-läsare ignorerar stilmallen. Texten i flödet visas alltid escapad (value-of, aldrig
     disable-output-escaping); eventuella HTML-taggar i description tas bort innan utdraget kortas. -->
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
<xsl:output method="html" encoding="UTF-8" indent="no" doctype-system="about:legacy-compat"/>

<xsl:variable name="self">
  <xsl:choose>
    <xsl:when test="/rss/channel/atom:link[@rel='self']/@href"><xsl:value-of select="/rss/channel/atom:link[@rel='self']/@href"/></xsl:when>
    <xsl:otherwise>https://motorpuls.se/feed.xml</xsl:otherwise>
  </xsl:choose>
</xsl:variable>

<xsl:template match="/">
<html lang="sv">
<head>
<meta charset="utf-8"/>
<meta name="viewport" content="width=device-width, initial-scale=1"/>
<meta name="robots" content="noindex"/>
<meta name="color-scheme" content="dark"/>
<meta name="theme-color" content="#0B0D10"/>
<title>RSS: <xsl:value-of select="/rss/channel/title"/></title>
<link rel="icon" href="/favicon/favicon.svg" type="image/svg+xml"/>
<style>
@font-face{font-family:"Archivo";src:url(/fonts/archivo-var.woff2) format("woff2");font-weight:400 820;font-stretch:100% 115%;font-display:swap}
@font-face{font-family:"Newsreader";src:url(/fonts/newsreader-var.woff2) format("woff2");font-weight:400 700;font-display:swap;size-adjust:123.474178%}
@font-face{font-family:"DM Mono";src:url(/fonts/dmmono-400.woff2) format("woff2");font-weight:400;font-display:swap;size-adjust:106.048387%}
:root{color-scheme:dark;--bg:#0B0D10;--surface:#151A20;--line:#252C35;--line-strong:#3A434E;--text:#EEF1F4;--text-2:#C3CAD1;--muted:#929CA7;
  --pulse:#FF5B1F;--pulse-text:#FF8A5C;--glow:rgb(255 91 31 / .16);
  --sans:"Archivo",ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto,Arial,sans-serif;
  --serif:"Newsreader",ui-serif,Georgia,"Times New Roman",serif;
  --mono:"DM Mono",ui-monospace,"SFMono-Regular",Menlo,Consolas,monospace;
  --gutter:clamp(1.25rem,4vw,2.5rem);--radius:4px}
*,*::before,*::after{box-sizing:border-box}
html{-webkit-text-size-adjust:100%;text-size-adjust:100%;background:var(--bg)}
body{margin:0;color:var(--text);font-family:var(--sans);font-size:1rem;line-height:1.5;-webkit-font-smoothing:antialiased;
  background:radial-gradient(60rem 28rem at 30% -6rem,var(--glow),transparent 70%),linear-gradient(180deg,#0E1116 0,var(--bg) 40rem);
  background-repeat:no-repeat;background-color:var(--bg)}
a{color:inherit}
h1,h2,p{margin:0}
:focus-visible{outline:2px solid var(--text);outline-offset:3px;box-shadow:0 0 0 5px rgb(255 91 31 / .55);border-radius:2px}
.skip{position:absolute;left:var(--gutter);top:-3rem;background:var(--text);color:var(--bg);padding:.6rem 1rem;z-index:60;text-decoration:none}
.skip:focus{top:.75rem}
.wrap{max-width:48rem;margin-inline:auto;padding-inline:var(--gutter)}
.masthead{background:#0B0D10;border-bottom:1px solid var(--line)}
.masthead .wrap{display:flex;align-items:center;justify-content:space-between;gap:1rem;height:64px}
.wordmark{display:inline-flex;align-items:center;text-decoration:none}
.logo{height:clamp(1.15rem,1.6vw + .55rem,1.45rem);width:auto;display:block;transform:translateY(8%)}
.rss-icon{flex:none}
main{padding-block:clamp(2rem,5vw,3.5rem) 3rem}
.kicker{display:flex;align-items:center;gap:.5rem;font-family:var(--mono);font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;color:var(--pulse-text);margin-bottom:.6rem}
h1{font-size:clamp(1.9rem,4.2vw + .6rem,3rem);line-height:1.06;font-weight:800;font-stretch:115%;letter-spacing:-.02em;text-wrap:balance}
.lede{font-family:var(--serif);font-size:clamp(1.05rem,.4vw + .95rem,1.2rem);line-height:1.5;color:var(--text-2);margin-top:.9rem;max-width:40rem}
.about{margin-top:1.75rem;background:var(--surface);border:1px solid var(--line);border-top:2px solid var(--pulse);border-radius:var(--radius);padding:1.1rem 1.25rem 1.25rem}
.about h2{font-size:1rem;font-weight:750;font-stretch:110%;margin-bottom:.4rem}
.about p{color:var(--text-2);line-height:1.55}
.url-label{display:block;font-family:var(--mono);font-size:.8rem;color:var(--muted);margin-top:1rem;margin-bottom:.35rem}
.url-row{display:flex;flex-wrap:wrap;gap:.5rem}
.url{flex:1 1 16rem;min-width:0;font-family:var(--mono);font-size:.9rem;color:var(--text);background:var(--bg);border:1px solid #6B7682;border-radius:var(--radius);padding:.65rem .75rem;min-height:2.875rem}
.copy{font:inherit;font-weight:700;font-size:.95rem;background:var(--pulse);color:#0B0D10;border:0;border-radius:var(--radius);padding:.65rem 1.1rem;min-height:2.875rem;cursor:pointer}
.copy:hover{background:#FF7440}
.copy[hidden]{display:none}
.status{min-height:1.5em;margin-top:.4rem;font-size:.9rem;color:var(--pulse-text)}
.list-h{font-family:var(--mono);font-size:.85rem;font-weight:400;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);margin-top:2.75rem;padding-bottom:.6rem;border-bottom:1px solid var(--line-strong)}
ol.items{list-style:none;margin:0;padding:0}
.item{padding-block:1.25rem;border-bottom:1px solid var(--line)}
.meta{display:flex;flex-wrap:wrap;gap:.2rem .75rem;font-family:var(--mono);font-size:.8rem;color:var(--muted);margin-bottom:.35rem}
.meta .cat{color:var(--pulse-text);text-transform:uppercase;letter-spacing:.05em}
.item h3{margin:0;font-size:clamp(1.1rem,.8vw + .95rem,1.35rem);line-height:1.2;font-weight:750;font-stretch:108%;letter-spacing:-.01em;text-wrap:balance}
.item h3 a{text-decoration:none}
.item h3 a:hover{text-decoration:underline;text-decoration-color:var(--pulse);text-underline-offset:.18em}
.item p{font-family:var(--serif);color:var(--text-2);margin-top:.45rem;line-height:1.55}
.foot{border-top:1px solid var(--line);padding-block:1.5rem 2.5rem;color:var(--muted);font-size:.9rem}
.foot a{color:var(--text);text-underline-offset:.2em}
@media (prefers-reduced-motion:no-preference){.copy{transition:background-color .18s}}
</style>
</head>
<body>
<a class="skip" href="#innehall">Till innehållet</a>
<header class="masthead">
  <div class="wrap">
    <a class="wordmark" href="/"><img class="logo" src="/img/logo.svg" alt="Motorpuls" width="872" height="88"/></a>
  </div>
</header>
<main id="innehall" class="wrap">
  <p class="kicker"><svg class="rss-icon" viewBox="0 0 16 16" width="16" height="16" aria-hidden="true" focusable="false"><rect width="16" height="16" rx="3" fill="#FF5B1F"/><circle cx="4.6" cy="11.4" r="1.5" fill="#0B0D10"/><path d="M3.2 7.1a5.7 5.7 0 0 1 5.7 5.7M3.2 3.6a9.2 9.2 0 0 1 9.2 9.2" fill="none" stroke="#0B0D10" stroke-width="1.8" stroke-linecap="round"/></svg>RSS-flöde</p>
  <h1><xsl:value-of select="/rss/channel/title"/></h1>
  <p class="lede"><xsl:value-of select="/rss/channel/description"/></p>
  <section class="about" aria-labelledby="om-flodet">
    <h2 id="om-flodet">Så prenumererar du</h2>
    <p>Det här är ett RSS-flöde. Kopiera adressen till din RSS-läsare, till exempel Feedly, Inoreader eller Reeder, så får du nya artiklar direkt.</p>
    <label class="url-label" for="flodesadress">Flödets adress</label>
    <div class="url-row">
      <input class="url" id="flodesadress" type="text" readonly="readonly" spellcheck="false" value="{$self}"/>
      <button class="copy" id="kopiera" type="button" hidden="hidden">Kopiera adressen</button>
    </div>
    <p class="status" id="kopiera-status" role="status"></p>
  </section>
  <h2 class="list-h" id="senaste">Senaste artiklarna</h2>
  <ol class="items" role="list" aria-labelledby="senaste">
    <xsl:apply-templates select="/rss/channel/item"/>
  </ol>
</main>
<footer class="foot">
  <div class="wrap">
    <p><a href="{/rss/channel/link}">Till <xsl:value-of select="/rss/channel/title"/></a></p>
  </div>
</footer>
<script>
(function(){
  var b=document.getElementById("kopiera"),f=document.getElementById("flodesadress"),s=document.getElementById("kopiera-status");
  f.addEventListener("focus",function(){f.select()});
  if(!b||!navigator.clipboard||!window.isSecureContext)return;
  b.hidden=false;
  b.addEventListener("click",function(){
    navigator.clipboard.writeText(f.value).then(function(){s.textContent="Adressen är kopierad."},
      function(){f.focus();f.select();s.textContent="Kopieringen gick inte, markera adressen och kopiera den själv."});
  });
})();
</script>
</body>
</html>
</xsl:template>

<xsl:template match="item">
  <li class="item">
    <p class="meta">
      <xsl:if test="pubDate"><xsl:call-template name="datum"><xsl:with-param name="d" select="normalize-space(pubDate)"/></xsl:call-template></xsl:if>
      <xsl:if test="category"><span class="cat"><xsl:value-of select="category[1]"/></span></xsl:if>
    </p>
    <h3>
      <xsl:choose>
        <xsl:when test="starts-with(normalize-space(link),'https://') or starts-with(normalize-space(link),'http://')"><a href="{normalize-space(link)}"><xsl:value-of select="title"/></a></xsl:when>
        <xsl:otherwise><xsl:value-of select="title"/></xsl:otherwise>
      </xsl:choose>
    </h3>
    <xsl:if test="normalize-space(description)">
      <xsl:variable name="txt"><xsl:call-template name="utan-taggar"><xsl:with-param name="s" select="description"/></xsl:call-template></xsl:variable>
      <xsl:variable name="t" select="normalize-space($txt)"/>
      <p>
        <xsl:choose>
          <xsl:when test="string-length($t) &gt; 320"><xsl:value-of select="substring($t,1,300)"/>…</xsl:when>
          <xsl:otherwise><xsl:value-of select="$t"/></xsl:otherwise>
        </xsl:choose>
      </p>
    </xsl:if>
  </li>
</xsl:template>

<!-- Tar bort allt mellan < och > (HTML i description, escapad i flödet). Resultatet skrivs ut escapat. -->
<xsl:template name="utan-taggar">
  <xsl:param name="s"/>
  <xsl:choose>
    <xsl:when test="contains($s,'&lt;')">
      <xsl:value-of select="substring-before($s,'&lt;')"/>
      <xsl:if test="contains(substring-after($s,'&lt;'),'&gt;')"><xsl:text> </xsl:text></xsl:if>
      <xsl:variable name="rest" select="substring-after($s,'&lt;')"/>
      <xsl:choose>
        <xsl:when test="contains($rest,'&gt;')">
          <xsl:call-template name="utan-taggar"><xsl:with-param name="s" select="substring-after($rest,'&gt;')"/></xsl:call-template>
        </xsl:when>
        <xsl:otherwise><xsl:value-of select="concat('&lt;',$rest)"/></xsl:otherwise>
      </xsl:choose>
    </xsl:when>
    <xsl:otherwise><xsl:value-of select="$s"/></xsl:otherwise>
  </xsl:choose>
</xsl:template>

<!-- RFC 822 ("Sun, 01 Nov 2026 08:00:00 +0100") till "1 november 2026, 08:00" -->
<xsl:template name="datum">
  <xsl:param name="d"/>
  <xsl:variable name="r" select="normalize-space(substring-after($d,','))"/>
  <xsl:variable name="dag" select="substring-before($r,' ')"/>
  <xsl:variable name="r2" select="substring-after($r,' ')"/>
  <xsl:variable name="man" select="substring-before($r2,' ')"/>
  <xsl:variable name="r3" select="substring-after($r2,' ')"/>
  <xsl:variable name="ar" select="substring-before($r3,' ')"/>
  <xsl:variable name="tid" select="substring(substring-after($r3,' '),1,5)"/>
  <xsl:variable name="nr" select="(string-length(substring-before('JanFebMarAprMayJunJulAugSepOctNovDec',$man)) div 3) + 1"/>
  <xsl:choose>
    <xsl:when test="string-length($man) = 3 and contains('JanFebMarAprMayJunJulAugSepOctNovDec',$man) and number($dag) = number($dag)">
      <time datetime="{$ar}-{format-number($nr,'00')}-{format-number($dag,'00')}T{$tid}">
        <xsl:value-of select="number($dag)"/><xsl:text> </xsl:text>
        <xsl:value-of select="substring-before(substring-after('|1januari|2februari|3mars|4april|5maj|6juni|7juli|8augusti|9september|10oktober|11november|12december|', concat('|',$nr)),'|')"/>
        <xsl:text> </xsl:text><xsl:value-of select="$ar"/><xsl:text>, </xsl:text><xsl:value-of select="$tid"/>
      </time>
    </xsl:when>
    <xsl:otherwise><xsl:value-of select="$d"/></xsl:otherwise>
  </xsl:choose>
</xsl:template>

</xsl:stylesheet>
