"""
Health check endpoint for Vercel deployment monitoring
"""


def handler(request):
    """
    Simple health check endpoint
    Returns OK if the deployment is working
    """

    try:
        from config import BOT_TOKEN, DATABASE_URL, AWS_S3_BUCKET

        health_status = {
            "status": "healthy",
            "services": {
                "bot_token": "✓" if BOT_TOKEN else "✗",
                "database": "✓" if DATABASE_URL else "✗",
                "s3_storage": "✓" if AWS_S3_BUCKET else "✗",
            }
        }

        # Check if all critical services are configured
        all_configured = all(health_status["services"].values() == ["✓"])

        return {
            "statusCode": 200 if all_configured else 503,
            "body": health_status
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "error": str(e)
        }
