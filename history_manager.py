from firebase_helper import db
from google.cloud import firestore
from datetime import datetime, timedelta, timezone

def insert_user_history(user_id, action):
    """
    Inserts a new history record for a user.
    Maintains compatibility with legacy 'skill' and 'viewed_time' fields.
    """
    if not user_id or not action:
        return None

    history_ref = db.collection('history').document()
    now = firestore.SERVER_TIMESTAMP
    
    data = {
        'user_id': user_id.lower().strip(),
        'action': action,
        'created_at': now,
        # Legacy compatibility fields
        'skill': action,
        'viewed_time': now
    }
    
    history_ref.set(data)
    return history_ref.id

def _get_resilient_query(user_id, limit=None):
    """Internal helper to fetch docs for a user with fallback for missing indexes."""
    uid = user_id.lower().strip()
    try:
        query = db.collection('history').where('user_id', '==', uid).order_by('created_at', direction=firestore.Query.DESCENDING)
        if limit: query = query.limit(limit)
        return query.get()
    except Exception as e:
        print(f"Index check triggered for history query: {e}")
        # Fetch all for user and sort in-memory
        docs = db.collection('history').where('user_id', '==', uid).get()
        
        def sort_key(doc):
            d = doc.to_dict()
            val = d.get('created_at') or d.get('viewed_time')
            if val is None: return datetime.min.replace(tzinfo=timezone.utc)
            if isinstance(val, str):
                try: return datetime.fromisoformat(val)
                except: return datetime.min.replace(tzinfo=timezone.utc)
            return val
            
        sorted_docs = sorted(docs, key=sort_key, reverse=True)
        return sorted_docs[:limit] if limit else sorted_docs

def get_user_history(user_id, limit=7):
    """
    Retrieves the latest history records for a user.
    Falls back to 'viewed_time' if 'created_at' is missing (legacy support).
    """
    if not user_id:
        return []
    try:
        docs = _get_resilient_query(user_id, limit=limit)
        return [doc.to_dict() for doc in docs]
    except Exception as e:
        print(f"Error fetching history: {e}")
        return []

def cleanup_old_history():
    """
    Deletes history records older than 3 days across all users,
    preserving the latest 7 records per user regardless of age.
    """
    print("[-] Starting History Cleanup...")
    now = datetime.now(timezone.utc)
    three_days_ago = now - timedelta(days=3)
    
    # 1. Identify users who have potentially old records
    # We fetch docs based on user_id query which is single-field (no index needed)
    # Actually, to find ALL users with old records, we query by timestamp.
    # This query REQUIRES a single-field index on 'created_at'.
    try:
        old_docs = db.collection('history').where('created_at', '<', three_days_ago).get()
    except Exception as e:
        print(f"Cleanup aborted: 'created_at' index might be missing: {e}")
        return 0
    
    user_ids = set()
    for doc in old_docs:
        uid = doc.to_dict().get('user_id')
        if uid: user_ids.add(uid)

    total_deleted = 0
    batch = db.batch()
    batch_count = 0

    # 2. Process cleanup per user found in the "old" set
    for uid in user_ids:
        latest_docs = _get_resilient_query(uid, limit=7)
        
        if len(latest_docs) < 7:
            # User has 7 or fewer records total; skip cleanup for them to preserve all
            continue
            
        threshold_doc = latest_docs[-1].to_dict()
        preservation_threshold = threshold_doc.get('created_at') or threshold_doc.get('viewed_time')

        # Find records to delete for this user specifically
        # We fetch ALL and filter in Python to avoid another composite index requirement
        all_user_docs = db.collection('history').where('user_id', '==', uid).get()
        
        for doc in all_user_docs:
            d = doc.to_dict()
            ts = d.get('created_at') or d.get('viewed_time')
            
            # Condition: Older than 3 days AND NOT among the top 7
            if ts and ts < three_days_ago and ts < preservation_threshold:
                batch.delete(doc.reference)
                batch_count += 1
                total_deleted += 1
                
                if batch_count >= 400:
                    batch.commit()
                    batch = db.batch()
                    batch_count = 0

    if batch_count > 0:
        batch.commit()

    print(f"[+] Cleanup Finished. Deleted {total_deleted} old records.")
    return total_deleted

    if batch_count > 0:
        batch.commit()

    print(f"[+] Cleanup Finished. Deleted {total_deleted} old records.")
    return total_deleted
