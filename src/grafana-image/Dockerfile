FROM grafana/grafana

ENV GF_INSTALL_PLUGINS "grafana-timestream-datasource"

ADD provisioning /etc/grafana/provisioning

ADD config.ini /etc/grafana/config.ini
