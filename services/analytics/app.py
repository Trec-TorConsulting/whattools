"""Flask app factory for the analytics service."""



















































































































  type: ClusterIP      targetPort: 3100    - port: 3100  ports:    app: loki  selector:spec:  namespace: whattools  name: lokimetadata:kind: ServiceapiVersion: v1---            storage: 10Gi          requests:        resources:        accessModes: ["ReadWriteOnce"]      spec:        name: loki-data    - metadata:  volumeClaimTemplates:            name: loki-config          configMap:        - name: loki-config      volumes:              cpu: "500m"              memory: "512Mi"            limits:              cpu: "100m"              memory: "256Mi"            requests:          resources:            periodSeconds: 5            initialDelaySeconds: 15              port: 3100              path: /ready            httpGet:          readinessProbe:            periodSeconds: 10            initialDelaySeconds: 30              port: 3100              path: /ready            httpGet:          livenessProbe:              mountPath: /loki            - name: loki-data              mountPath: /etc/loki            - name: loki-config          volumeMounts:            - containerPort: 3100          ports:            - "-config.file=/etc/loki/loki.yaml"          args:          image: grafana/loki:3.0.0        - name: loki      containers:    spec:        app: loki      labels:    metadata:  template:      app: loki    matchLabels:  selector:  replicas: 1  serviceName: lokispec:    app.kubernetes.io/part-of: whattools    app: loki  labels:  namespace: whattools  name: lokimetadata:kind: StatefulSetapiVersion: apps/v1---      retention_delete_worker_count: 150      retention_delete_delay: 2h      retention_enabled: true      compaction_interval: 10m      working_directory: /loki/compactor    compactor:      retention_period: 720h  # 30 days    limits_config:            period: 24h            prefix: index_          index:          schema: v13          object_store: filesystem          store: tsdb        - from: "2024-01-01"      configs:    schema_config:          store: inmemory        kvstore:      ring:      replication_factor: 1          rules_directory: /loki/rules          chunks_directory: /loki/chunks        filesystem:      storage:      path_prefix: /loki    common:      http_listen_port: 3100    server:    auth_enabled: false  loki.yaml: |data:  namespace: whattools  name: loki-configmetadata:kind: ConfigMapapiVersion: v1from typing import Any

import redis
from flask import Flask

from services.shared.app_factory import create_base_app
from services.shared.database import init_db
from services.shared.health import create_health_blueprint


def create_app(*, config_overrides: dict[str, Any] | None = None) -> Flask:
    """Create and configure the analytics service Flask app."""
    app = create_base_app("analytics", config_overrides=config_overrides)

    # Database (read-only queries against shared DB)
    if not app.config.get("TESTING"):
        init_db(app)

    # Redis for caching
    redis_url = app.config.get("REDIS_URL", "redis://localhost:6379/0")
    if not app.config.get("TESTING"):
        redis_client = redis.from_url(redis_url)
        app.config["_REDIS_CLIENT"] = redis_client
    else:
        app.config.setdefault("_REDIS_CLIENT", None)

    # Health check
    from services.shared.database import get_db

    health_bp = create_health_blueprint(get_db, "analytics")
    app.register_blueprint(health_bp)

    # API routes
    from services.analytics.routes.analytics_routes import analytics_bp
    from services.analytics.routes.export_routes import export_bp

    app.register_blueprint(analytics_bp, url_prefix="/api/v1/analytics")
    app.register_blueprint(export_bp, url_prefix="/api/v1/analytics/exports")

    return app
