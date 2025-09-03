"""
admin_api.py - Admin API Endpoints for System Management
Add these endpoints to your main backend_api.py file
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from datetime import datetime, timedelta
import csv
import io
import os
from fastapi.responses import StreamingResponse
import subprocess
import psutil
from .utils.security_simple import get_current_coach

router = APIRouter()

# Admin authentication decorator
async def verify_admin_access(current_coach: dict = Depends(get_current_coach)):
    """Verify admin access (implement your admin logic here)"""
    # For now, checking if coach has admin flag or is in admin list
    admin_coaches = os.getenv("ADMIN_COACH_IDS", "").split(",")
    
    if str(current_coach["id"]) not in admin_coaches:
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return current_coach

# System Statistics Endpoints

@router.get("/stats")
async def get_system_stats(
    range_param: str = Query("7d", alias="range"),
    admin: dict = Depends(verify_admin_access)
):
    """Get comprehensive system statistics"""
    try:
        # Parse time range
        if range_param == "1d":
            start_date = datetime.now() - timedelta(days=1)
        elif range_param == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif range_param == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif range_param == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=7)
        
        async with db.pool.acquire() as conn:
            # Basic counts
            basic_stats = await conn.fetchrow(
                """SELECT 
                    (SELECT COUNT(*) FROM coaches WHERE is_active = true) as total_coaches,
                    (SELECT COUNT(*) FROM clients WHERE is_active = true) as total_clients,
                    (SELECT COUNT(*) FROM message_history WHERE sent_at >= $1) as messages_sent,
                    (SELECT COUNT(*) FROM scheduled_messages WHERE status = 'scheduled') as pending_messages,
                    (SELECT COUNT(DISTINCT coach_id) FROM message_history WHERE sent_at >= CURRENT_DATE) as active_coaches_today""",
                start_date
            )
            
            # Success rate calculation
            success_stats = await conn.fetchrow(
                """SELECT 
                    COUNT(*) as total_attempts,
                    COUNT(CASE WHEN delivery_status IN ('delivered', 'read') THEN 1 END) as successful_deliveries
                FROM message_history WHERE sent_at >= $1""",
                start_date
            )
            
            success_rate = 0
            if success_stats['total_attempts'] > 0:
                success_rate = (success_stats['successful_deliveries'] / success_stats['total_attempts']) * 100
            
            # Daily message breakdown
            daily_messages = await conn.fetch(
                """SELECT 
                    DATE(sent_at) as date,
                    COUNT(CASE WHEN message_type = 'celebration' THEN 1 END) as celebration,
                    COUNT(CASE WHEN message_type = 'accountability' THEN 1 END) as accountability,
                    COUNT(*) as total
                FROM message_history 
                WHERE sent_at >= $1
                GROUP BY DATE(sent_at)
                ORDER BY DATE(sent_at)""",
                start_date
            )
            
            # Message type distribution
            message_types = await conn.fetch(
                """SELECT 
                    message_type,
                    COUNT(*) as count
                FROM message_history 
                WHERE sent_at >= $1
                GROUP BY message_type""",
                start_date
            )
            
            return {
                "total_coaches": basic_stats['total_coaches'],
                "total_clients": basic_stats['total_clients'],
                "messages_sent": basic_stats['messages_sent'],
                "pending_messages": basic_stats['pending_messages'],
                "active_coaches_today": basic_stats['active_coaches_today'],
                "success_rate": round(success_rate, 1),
                "daily_messages": [
                    {
                        "date": msg['date'].strftime('%Y-%m-%d'),
                        "celebration": msg['celebration'],
                        "accountability": msg['accountability'],
                        "total": msg['total']
                    } for msg in daily_messages
                ],
                "message_distribution": {
                    msg_type['message_type']: msg_type['count'] 
                    for msg_type in message_types
                }
            }
    
    except Exception as e:
        logger.error(f"Get system stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system statistics")

@router.get("/coaches")
async def get_all_coaches(admin: dict = Depends(verify_admin_access)):
    """Get all coaches with their statistics"""
    try:
        async with db.pool.acquire() as conn:
            coaches = await conn.fetch(
                """SELECT 
                    c.id,
                    c.name,
                    c.email,
                    c.timezone,
                    c.last_login,
                    c.created_at,
                    c.is_active,
                    COUNT(DISTINCT cl.id) as client_count,
                    COUNT(DISTINCT mh.id) as total_messages_sent,
                    MAX(mh.sent_at) as last_message_sent
                FROM coaches c
                LEFT JOIN clients cl ON c.id = cl.coach_id AND cl.is_active = true
                LEFT JOIN message_history mh ON c.id = mh.coach_id
                GROUP BY c.id, c.name, c.email, c.timezone, c.last_login, c.created_at, c.is_active
                ORDER BY c.last_login DESC NULLS LAST""",
            )
            
            return [
                {
                    "id": str(coach['id']),
                    "name": coach['name'],
                    "email": coach['email'],
                    "timezone": coach['timezone'],
                    "clients": coach['client_count'],
                    "messages_sent": coach['total_messages_sent'],
                    "last_active": coach['last_login'].isoformat() if coach['last_login'] else None,
                    "last_message_sent": coach['last_message_sent'].isoformat() if coach['last_message_sent'] else None,
                    "status": "active" if coach['is_active'] else "inactive",
                    "member_since": coach['created_at'].isoformat()
                } for coach in coaches
            ]
    
    except Exception as e:
        logger.error(f"Get all coaches error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch coaches")

@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(50, le=200),
    admin: dict = Depends(verify_admin_access)
):
    """Get recent system activity"""
    try:
        async with db.pool.acquire() as conn:
            # Combine different types of activities
            activities = []
            
            # Recent message activities
            message_activities = await conn.fetch(
                """SELECT 
                    'message_sent' as activity_type,
                    CONCAT(co.name, ' sent ', mh.message_type, ' to ', c.name) as description,
                    mh.sent_at as timestamp,
                    mh.delivery_status as status
                FROM message_history mh
                JOIN coaches co ON mh.coach_id = co.id
                JOIN clients c ON mh.client_id = c.id
                ORDER BY mh.sent_at DESC
                LIMIT $1""",
                limit // 2
            )
            
            # Recent registrations
            registration_activities = await conn.fetch(
                """SELECT 
                    'coach_registered' as activity_type,
                    CONCAT('New coach registered: ', name) as description,
                    created_at as timestamp,
                    'success' as status
                FROM coaches
                ORDER BY created_at DESC
                LIMIT $1""",
                limit // 4
            )
            
            # Recent voice processing
            voice_activities = await conn.fetch(
                """SELECT 
                    'voice_processed' as activity_type,
                    CONCAT('Voice message processed for coach ID: ', coach_id) as description,
                    updated_at as timestamp,
                    processing_status as status
                FROM voice_message_processing
                WHERE processing_status IN ('confirmed', 'failed')
                ORDER BY updated_at DESC
                LIMIT $1""",
                limit // 4
            )
            
            # Combine and sort all activities
            all_activities = []
            
            for activity in message_activities:
                all_activities.append({
                    "type": activity['activity_type'],
                    "description": activity['description'],
                    "timestamp": activity['timestamp'].isoformat(),
                    "status": activity['status']
                })
            
            for activity in registration_activities:
                all_activities.append({
                    "type": activity['activity_type'],
                    "description": activity['description'],
                    "timestamp": activity['timestamp'].isoformat(),
                    "status": activity['status']
                })
            
            for activity in voice_activities:
                all_activities.append({
                    "type": activity['activity_type'],
                    "description": activity['description'],
                    "timestamp": activity['timestamp'].isoformat(),
                    "status": activity['status']
                })
            
            # Sort by timestamp
            all_activities.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return all_activities[:limit]
    
    except Exception as e:
        logger.error(f"Get recent activity error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent activity")

@router.get("/export-report")
async def export_system_report(
    range_param: str = Query("30d", alias="range"),
    admin: dict = Depends(verify_admin_access)
):
    """Export comprehensive system report as CSV"""
    try:
        # Parse time range
        if range_param == "1d":
            start_date = datetime.now() - timedelta(days=1)
        elif range_param == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif range_param == "30d":
            start_date = datetime.now() - timedelta(days=30)
        elif range_param == "90d":
            start_date = datetime.now() - timedelta(days=90)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        async with db.pool.acquire() as conn:
            # Get comprehensive report data
            report_data = await conn.fetch(
                """SELECT 
                    co.name as coach_name,
                    co.email as coach_email,
                    c.name as client_name,
                    c.phone_number,
                    c.country,
                    c.timezone as client_timezone,
                    mh.message_type,
                    mh.content,
                    mh.delivery_status,
                    mh.sent_at,
                    mh.delivered_at,
                    mh.read_at,
                    STRING_AGG(DISTINCT cat.name, ', ') as client_categories
                FROM message_history mh
                JOIN coaches co ON mh.coach_id = co.id
                JOIN clients c ON mh.client_id = c.id
                LEFT JOIN client_categories cc ON c.id = cc.client_id
                LEFT JOIN categories cat ON cc.category_id = cat.id
                WHERE mh.sent_at >= $1
                GROUP BY co.id, co.name, co.email, c.id, c.name, c.phone_number, 
                         c.country, c.timezone, mh.id, mh.message_type, mh.content, 
                         mh.delivery_status, mh.sent_at, mh.delivered_at, mh.read_at
                ORDER BY mh.sent_at DESC""",
                start_date
            )
            
            # Create CSV content
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write headers
            headers = [
                'Coach Name', 'Coach Email', 'Client Name', 'Phone Number', 'Country',
                'Client Timezone', 'Message Type', 'Content', 'Delivery Status',
                'Sent At', 'Delivered At', 'Read At', 'Client Categories'
            ]
            writer.writerow(headers)
            
            # Write data
            for row in report_data:
                writer.writerow([
                    row['coach_name'],
                    row['coach_email'],
                    row['client_name'],
                    row['phone_number'],
                    row['country'],
                    row['client_timezone'],
                    row['message_type'],
                    row['content'][:100] + '...' if len(row['content']) > 100 else row['content'],
                    row['delivery_status'],
                    row['sent_at'].isoformat() if row['sent_at'] else '',
                    row['delivered_at'].isoformat() if row['delivered_at'] else '',
                    row['read_at'].isoformat() if row['read_at'] else '',
                    row['client_categories'] or ''
                ])
            
            output.seek(0)
            
            # Return CSV as streaming response
            return StreamingResponse(
                io.BytesIO(output.getvalue().encode('utf-8')),
                media_type="text/csv",
                headers={
                    "Content-Disposition": f"attachment; filename=coaching-system-report-{datetime.now().strftime('%Y-%m-%d')}.csv"
                }
            )
    
    except Exception as e:
        logger.error(f"Export report error: {e}")
        raise HTTPException(status_code=500, detail="Failed to export report")

@router.get("/coaches/{coach_id}/detailed")
async def get_coach_detailed_stats(
    coach_id: str,
    admin: dict = Depends(verify_admin_access)
):
    """Get detailed statistics for specific coach"""
    try:
        async with db.pool.acquire() as conn:
            # Coach basic info
            coach_info = await conn.fetchrow(
                "SELECT * FROM coaches WHERE id = $1",
                coach_id
            )
            
            if not coach_info:
                raise HTTPException(status_code=404, detail="Coach not found")
            
            # Client statistics
            client_stats = await conn.fetch(
                """SELECT 
                    c.name,
                    c.phone_number,
                    c.country,
                    c.timezone,
                    COUNT(mh.id) as total_messages,
                    COUNT(CASE WHEN mh.delivery_status = 'delivered' THEN 1 END) as delivered_messages,
                    COUNT(CASE WHEN mh.delivery_status = 'read' THEN 1 END) as read_messages,
                    MAX(mh.sent_at) as last_message_sent,
                    STRING_AGG(DISTINCT cat.name, ', ') as categories
                FROM clients c
                LEFT JOIN message_history mh ON c.id = mh.client_id
                LEFT JOIN client_categories cc ON c.id = cc.client_id
                LEFT JOIN categories cat ON cc.category_id = cat.id
                WHERE c.coach_id = $1 AND c.is_active = true
                GROUP BY c.id, c.name, c.phone_number, c.country, c.timezone
                ORDER BY total_messages DESC""",
                coach_id
            )
            
            # Message trends (last 30 days)
            message_trends = await conn.fetch(
                """SELECT 
                    DATE(sent_at) as date,
                    COUNT(*) as total_messages,
                    COUNT(CASE WHEN message_type = 'celebration' THEN 1 END) as celebrations,
                    COUNT(CASE WHEN message_type = 'accountability' THEN 1 END) as accountability
                FROM message_history
                WHERE coach_id = $1 AND sent_at >= $2
                GROUP BY DATE(sent_at)
                ORDER BY DATE(sent_at)""",
                coach_id, datetime.now() - timedelta(days=30)
            )
            
            return {
                "coach_info": {
                    "id": str(coach_info['id']),
                    "name": coach_info['name'],
                    "email": coach_info['email'],
                    "timezone": coach_info['timezone'],
                    "created_at": coach_info['created_at'].isoformat(),
                    "last_login": coach_info['last_login'].isoformat() if coach_info['last_login'] else None,
                    "is_active": coach_info['is_active']
                },
                "client_stats": [
                    {
                        "name": client['name'],
                        "phone_number": client['phone_number'],
                        "country": client['country'],
                        "timezone": client['timezone'],
                        "total_messages": client['total_messages'],
                        "delivered_messages": client['delivered_messages'],
                        "read_messages": client['read_messages'],
                        "engagement_rate": round((client['read_messages'] / client['total_messages'] * 100), 1) if client['total_messages'] > 0 else 0,
                        "last_message_sent": client['last_message_sent'].isoformat() if client['last_message_sent'] else None,
                        "categories": client['categories']
                    } for client in client_stats
                ],
                "message_trends": [
                    {
                        "date": trend['date'].strftime('%Y-%m-%d'),
                        "total": trend['total_messages'],
                        "celebrations": trend['celebrations'],
                        "accountability": trend['accountability']
                    } for trend in message_trends
                ]
            }
    
    except Exception as e:
        logger.error(f"Get coach detailed stats error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch coach statistics")

@router.post("/coaches/{coach_id}/suspend")
async def suspend_coach(
    coach_id: str,
    reason: str,
    admin: dict = Depends(verify_admin_access)
):
    """Suspend a coach account"""
    try:
        async with db.pool.acquire() as conn:
            # Update coach status
            await conn.execute(
                "UPDATE coaches SET is_active = false, updated_at = $1 WHERE id = $2",
                datetime.now(), coach_id
            )
            
            # Cancel all scheduled messages
            cancelled_count = await conn.fetchval(
                """UPDATE scheduled_messages 
                   SET status = 'cancelled' 
                   WHERE coach_id = $1 AND status = 'scheduled'
                   RETURNING COUNT(*)""",
                coach_id
            )
            
            # Log the suspension
            await conn.execute(
                """INSERT INTO admin_actions (admin_id, action_type, target_id, details, created_at)
                   VALUES ($1, 'suspend_coach', $2, $3, $4)""",
                admin['id'], coach_id, f"Reason: {reason}", datetime.now()
            )
            
            return {
                "status": "suspended",
                "cancelled_messages": cancelled_count,
                "reason": reason
            }
    
    except Exception as e:
        logger.error(f"Suspend coach error: {e}")
        raise HTTPException(status_code=500, detail="Failed to suspend coach")

@router.post("/system/restart")
async def restart_system_services(admin: dict = Depends(verify_admin_access)):
    """Restart system services (use with caution)"""
    try:
        # This is a dangerous operation - implement with proper safeguards
        logger.warning(f"System restart initiated by admin {admin['name']}")
        
        # In production, this would trigger a graceful restart
        # For now, just restart background workers
        
        # Kill and restart Celery workers
        subprocess.run(["pkill", "-f", "celery.*worker"], check=False)
        subprocess.Popen(["celery", "-A", "worker:celery_app", "worker", "--detach"])
        
        # Restart beat scheduler
        subprocess.run(["pkill", "-f", "celery.*beat"], check=False)
        subprocess.Popen(["celery", "-A", "worker:celery_app", "beat", "--detach"])
        
        return {"status": "restart_initiated", "message": "Background services restarting..."}
    
    except Exception as e:
        logger.error(f"System restart error: {e}")
        raise HTTPException(status_code=500, detail="Failed to restart services")

@router.get("/system/performance")
async def get_system_performance(admin: dict = Depends(verify_admin_access)):
    """Get real-time system performance metrics"""
    try:
        # System resources
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database performance
        async with db.pool.acquire() as conn:
            db_stats = await conn.fetchrow(
                """SELECT 
                    (SELECT COUNT(*) FROM pg_stat_activity WHERE state = 'active') as active_connections,
                    (SELECT COUNT(*) FROM pg_stat_activity) as total_connections,
                    (SELECT pg_size_pretty(pg_database_size(current_database()))) as database_size""",
            )
            
            # Recent query performance
            slow_queries = await conn.fetch(
                """SELECT 
                    query,
                    mean_exec_time,
                    calls,
                    total_exec_time
                FROM pg_stat_statements 
                WHERE mean_exec_time > 100
                ORDER BY mean_exec_time DESC
                LIMIT 10""",
            )
        
        return {
            "system": {
                "cpu_percent": cpu_percent,
                "memory_percent": memory.percent,
                "disk_percent": (disk.used / disk.total) * 100,
                "disk_free": f"{disk.free // (1024**3)}GB"
            },
            "database": {
                "active_connections": db_stats['active_connections'],
                "total_connections": db_stats['total_connections'],
                "database_size": db_stats['database_size'],
                "slow_queries": [
                    {
                        "query": query['query'][:100] + "..." if len(query['query']) > 100 else query['query'],
                        "avg_time_ms": round(query['mean_exec_time'], 2),
                        "total_calls": query['calls']
                    } for query in slow_queries
                ]
            }
        }
    
    except Exception as e:
        logger.error(f"Get system performance error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch performance metrics")

@router.post("/maintenance/cleanup")
async def trigger_maintenance_cleanup(admin: dict = Depends(verify_admin_access)):
    """Trigger manual maintenance cleanup"""
    try:
        # Queue cleanup task
        from worker import cleanup_old_data
        task = cleanup_old_data.delay()
        
        return {
            "status": "cleanup_initiated",
            "task_id": task.id,
            "message": "Maintenance cleanup started in background"
        }
    
    except Exception as e:
        logger.error(f"Maintenance cleanup error: {e}")
        raise HTTPException(status_code=500, detail="Failed to initiate cleanup")

@router.get("/logs")
async def get_system_logs(
    level: str = Query("INFO", regex="^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$"),
    limit: int = Query(100, le=1000),
    admin: dict = Depends(verify_admin_access)
):
    """Get recent system logs"""
    try:
        # Read log files (this is a simplified version)
        log_entries = []
        
        log_files = ['/app/logs/app.log', '/app/logs/errors.log', '/app/logs/webhooks.log']
        
        for log_file in log_files:
            try:
                if os.path.exists(log_file):
                    with open(log_file, 'r') as f:
                        lines = f.readlines()[-limit:]
                        for line in lines:
                            if level.upper() in line.upper():
                                log_entries.append({
                                    "timestamp": line.split(' - ')[0] if ' - ' in line else '',
                                    "level": level,
                                    "message": line.strip(),
                                    "source": log_file.split('/')[-1]
                                })
            except Exception as e:
                logger.error(f"Error reading log file {log_file}: {e}")
        
        # Sort by timestamp (most recent first)
        log_entries.sort(key=lambda x: x['timestamp'], reverse=True)
        
        return log_entries[:limit]
    
    except Exception as e:
        logger.error(f"Get system logs error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch system logs")

@router.post("/coaches/{coach_id}/reset-api")
async def reset_coach_whatsapp_api(
    coach_id: str,
    new_token: str,
    admin: dict = Depends(verify_admin_access)
):
    """Reset coach's WhatsApp API token"""
    try:
        async with db.pool.acquire() as conn:
            # Update WhatsApp token
            await conn.execute(
                "UPDATE coaches SET whatsapp_token = $1, updated_at = $2 WHERE id = $3",
                new_token, datetime.now(), coach_id
            )
            
            # Log the action
            await conn.execute(
                """INSERT INTO admin_actions (admin_id, action_type, target_id, details, created_at)
                   VALUES ($1, 'reset_api_token', $2, 'WhatsApp API token reset', $3)""",
                admin['id'], coach_id, datetime.now()
            )
            
            return {"status": "token_updated", "coach_id": coach_id}
    
    except Exception as e:
        logger.error(f"Reset API token error: {e}")
        raise HTTPException(status_code=500, detail="Failed to reset API token")

@router.get("/analytics/summary")
async def get_analytics_summary(
    range_param: str = Query("30d", alias="range"),
    admin: dict = Depends(verify_admin_access)
):
    """Get high-level analytics summary"""
    try:
        if range_param == "1d":
            start_date = datetime.now() - timedelta(days=1)
        elif range_param == "7d":
            start_date = datetime.now() - timedelta(days=7)
        elif range_param == "30d":
            start_date = datetime.now() - timedelta(days=30)
        else:
            start_date = datetime.now() - timedelta(days=30)
        
        async with db.pool.acquire() as conn:
            # Overall metrics
            overall = await conn.fetchrow(
                """SELECT 
                    COUNT(DISTINCT coach_id) as active_coaches,
                    COUNT(DISTINCT client_id) as reached_clients,
                    COUNT(*) as total_messages,
                    AVG(CASE WHEN delivery_status = 'read' THEN 1 ELSE 0 END) * 100 as avg_engagement_rate,
                    COUNT(CASE WHEN message_type = 'celebration' THEN 1 END) as celebration_messages,
                    COUNT(CASE WHEN message_type = 'accountability' THEN 1 END) as accountability_messages
                FROM message_history
                WHERE sent_at >= $1""",
                start_date
            )
            
            # Top performing coaches
            top_coaches = await conn.fetch(
                """SELECT 
                    co.name,
                    COUNT(mh.id) as messages_sent,
                    COUNT(CASE WHEN mh.delivery_status = 'read' THEN 1 END) as messages_read,
                    COUNT(DISTINCT mh.client_id) as active_clients
                FROM coaches co
                JOIN message_history mh ON co.id = mh.coach_id
                WHERE mh.sent_at >= $1
                GROUP BY co.id, co.name
                ORDER BY messages_sent DESC
                LIMIT 10""",
                start_date
            )
            
            # Client engagement by category
            category_engagement = await conn.fetch(
                """SELECT 
                    cat.name as category,
                    COUNT(mh.id) as messages_sent,
                    COUNT(CASE WHEN mh.delivery_status = 'read' THEN 1 END) as messages_read,
                    COUNT(DISTINCT mh.client_id) as clients_in_category
                FROM categories cat
                JOIN client_categories cc ON cat.id = cc.category_id
                JOIN clients c ON cc.client_id = c.id
                JOIN message_history mh ON c.id = mh.client_id
                WHERE mh.sent_at >= $1
                GROUP BY cat.id, cat.name
                ORDER BY messages_sent DESC""",
                start_date
            )
            
            return {
                "overview": {
                    "active_coaches": overall['active_coaches'],
                    "reached_clients": overall['reached_clients'],
                    "total_messages": overall['total_messages'],
                    "avg_engagement_rate": round(overall['avg_engagement_rate'], 1),
                    "celebration_messages": overall['celebration_messages'],
                    "accountability_messages": overall['accountability_messages']
                },
                "top_coaches": [
                    {
                        "name": coach['name'],
                        "messages_sent": coach['messages_sent'],
                        "messages_read": coach['messages_read'],
                        "active_clients": coach['active_clients'],
                        "engagement_rate": round((coach['messages_read'] / coach['messages_sent'] * 100), 1) if coach['messages_sent'] > 0 else 0
                    } for coach in top_coaches
                ],
                "category_performance": [
                    {
                        "category": cat['category'],
                        "messages_sent": cat['messages_sent'],
                        "messages_read": cat['messages_read'],
                        "clients": cat['clients_in_category'],
                        "engagement_rate": round((cat['messages_read'] / cat['messages_sent'] * 100), 1) if cat['messages_sent'] > 0 else 0
                    } for cat in category_engagement
                ]
            }
    
    except Exception as e:
        logger.error(f"Get analytics summary error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch analytics summary")

@router.get("/system/queue-status")
async def get_queue_status(admin: dict = Depends(verify_admin_access)):
    """Get background task queue status"""
    try:
        # Connect to Redis to get queue information
        import redis
        redis_client = redis.from_url(os.getenv("REDIS_URL"))
        
        # Get queue lengths
        queue_info = {}
        queues = ['messages', 'voice', 'sheets', 'bulk', 'celery']
        
        for queue in queues:
            try:
                length = redis_client.llen(queue)
                queue_info[queue] = length
            except:
                queue_info[queue] = 0
        
        # Get active tasks from database
        async with db.pool.acquire() as conn:
            pending_tasks = await conn.fetchrow(
                """SELECT 
                    COUNT(CASE WHEN status = 'scheduled' THEN 1 END) as scheduled_messages,
                    COUNT(CASE WHEN processing_status IN ('received', 'transcribed') THEN 1 END) as voice_processing,
                    COUNT(CASE WHEN sync_status = 'pending' THEN 1 END) as pending_syncs
                FROM scheduled_messages sm
                FULL OUTER JOIN voice_message_processing vmp ON true
                FULL OUTER JOIN google_sheets_sync gss ON true""",
            )
        
        return {
            "queue_lengths": queue_info,
            "pending_tasks": {
                "scheduled_messages": pending_tasks['scheduled_messages'] or 0,
                "voice_processing": pending_tasks['voice_processing'] or 0,
                "pending_syncs": pending_tasks['pending_syncs'] or 0
            },
            "total_pending": sum(queue_info.values())
        }
    
    except Exception as e:
        logger.error(f"Get queue status error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch queue status")

@router.post("/system/clear-cache")
async def clear_system_cache(admin: dict = Depends(verify_admin_access)):
    """Clear system caches"""
    try:
        import redis
        redis_client = redis.from_url(os.getenv("REDIS_URL"))
        
        # Clear Redis cache (be careful with this!)
        flushed_keys = redis_client.eval("""
            local keys = redis.call('keys', 'cache:*')
            if #keys > 0 then
                return redis.call('del', unpack(keys))
            else
                return 0
            end
        """, 0)
        
        logger.info(f"Cache cleared by admin {admin['name']}: {flushed_keys} keys removed")
        
        return {
            "status": "cache_cleared",
            "keys_removed": flushed_keys
        }
    
    except Exception as e:
        logger.error(f"Clear cache error: {e}")
        raise HTTPException(status_code=500, detail="Failed to clear cache")

@router.get("/errors/recent")
async def get_recent_errors(
    limit: int = Query(50, le=200),
    admin: dict = Depends(verify_admin_access)
):
    """Get recent system errors"""
    try:
        async with db.pool.acquire() as conn:
            # Get failed messages
            failed_messages = await conn.fetch(
                """SELECT 
                    'message_failure' as error_type,
                    CONCAT('Message to ', c.name, ' failed: ', mh.error_message) as description,
                    mh.sent_at as timestamp,
                    co.name as coach_name
                FROM message_history mh
                JOIN clients c ON mh.client_id = c.id
                JOIN coaches co ON mh.coach_id = co.id
                WHERE mh.delivery_status = 'failed'
                ORDER BY mh.sent_at DESC
                LIMIT $1""",
                limit // 2
            )
            
            # Get voice processing failures
            voice_failures = await conn.fetch(
                """SELECT 
                    'voice_failure' as error_type,
                    CONCAT('Voice processing failed for coach ID: ', coach_id) as description,
                    updated_at as timestamp,
                    coach_id
                FROM voice_message_processing
                WHERE processing_status = 'failed'
                ORDER BY updated_at DESC
                LIMIT $1""",
                limit // 2
            )
            
            # Combine and sort errors
            all_errors = []
            
            for error in failed_messages:
                all_errors.append({
                    "type": error['error_type'],
                    "description": error['description'],
                    "timestamp": error['timestamp'].isoformat(),
                    "coach_name": error['coach_name']
                })
            
            for error in voice_failures:
                all_errors.append({
                    "type": error['error_type'],
                    "description": error['description'],
                    "timestamp": error['timestamp'].isoformat(),
                    "coach_id": str(error['coach_id'])
                })
            
            all_errors.sort(key=lambda x: x['timestamp'], reverse=True)
            
            return all_errors[:limit]
    
    except Exception as e:
        logger.error(f"Get recent errors error: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch recent errors")

# Add admin actions tracking table to database schema
admin_actions_table = """
-- Add this to your database schema
CREATE TABLE IF NOT EXISTS admin_actions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    admin_id UUID NOT NULL REFERENCES coaches(id),
    action_type VARCHAR(50) NOT NULL,
    target_id UUID,
    details TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_admin_actions_admin_id ON admin_actions(admin_id);
CREATE INDEX idx_admin_actions_created_at ON admin_actions(created_at);
"""