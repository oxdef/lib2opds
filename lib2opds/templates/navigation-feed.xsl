{% extends "base.xsl" %}
{% block content %}
        <ul id="directories">
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
