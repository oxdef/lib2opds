{% extends "base.xsl" %}
{% block content %}
        <h1><xsl:value-of select="/atom:feed/atom:title"/></h1>
        <ul>
          <xsl:apply-templates select="/atom:feed/atom:entry" />
        </ul>
{% endblock %}
{% block templates %}
  <xsl:template match="atom:entry">
    <li>
        <xsl:element name="a">
            <xsl:attribute name="href">
                <xsl:value-of select="atom:link/@href"/>
            </xsl:attribute>
        <xsl:value-of select="atom:title"/>
        </xsl:element>
    </li>
  </xsl:template>
{% endblock %}
</xsl:stylesheet>
