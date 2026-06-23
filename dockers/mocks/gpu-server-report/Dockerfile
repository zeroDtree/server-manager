FROM alpine:3.21

RUN apk add --no-cache bash curl

COPY report-loop.sh /report-loop.sh
RUN chmod +x /report-loop.sh

ENV REPORT_API_URL=http://backend:8080
ENV AGENT_PSK=change-me-in-production
ENV AGENT_REPORT_INTERVAL=30

CMD ["/report-loop.sh"]
