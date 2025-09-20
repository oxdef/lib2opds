<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform" xmlns:atom="http://www.w3.org/2005/Atom">
  <xsl:output method="html" indent="yes" encoding="UTF-8"/>
  <xsl:template match="/">
  <html>
    <head>
      <meta charset="utf-8" />
      <meta http-equiv="Content-Security-Policy" content="default-src 'self'; script-src 'none'" />
      <link rel="stylesheet" type="text/css" href="{{ config.get_assets_uri() }}/style.css" />
      <title><xsl:value-of select="/atom:feed/atom:title"/></title>
    </head>
    <body>
    <xsl:apply-templates select="/atom:feed/atom:link[@rel='start']" />
    <xsl:apply-templates select="/atom:feed/atom:link[@rel='up']" />
      <div id="content">
      {% block content %}{% endblock %}
      </div>
      <hr />
      <div id="footer">Updated: <xsl:value-of select="/atom:feed/atom:updated"/>.</div>
    </body>
  </html>
  </xsl:template>
{% block templates %}{% endblock %}
  <xsl:template match="/atom:feed/atom:link[@rel='start']">
    <xsl:element name="a">
      <xsl:attribute name="href">
      <xsl:value-of select="./@href"/>
      </xsl:attribute>Home</xsl:element><xsl:text> / </xsl:text>
  </xsl:template>
  <xsl:template match="/atom:feed/atom:link[@rel='up']">
    <xsl:element name="a">
      <xsl:attribute name="href">
      <xsl:value-of select="./@href"/>
      </xsl:attribute>Up</xsl:element><xsl:text>  </xsl:text>
    <hr />
  </xsl:template>
</xsl:stylesheet>
