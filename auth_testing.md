# Auth-Gated App Testing Playbook

## Step 1: Create Test User & Session
Using MongoDB shell:

```
mongosh --eval "
use('test_database');
var userId = 'test-user-' + Date.now();
var sessionToken = 'test_session_' + Date.now();
db.users.insertOne({
  user_id: userId,
  email: 'test.user.' + Date.now() + '@example.com',
  name: 'Test User',
  picture: 'https://via.placeholder.com/150',
  role: 'USER',
  blocked: false,
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: userId,
  session_token: sessionToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Session token: ' + sessionToken);
print('User ID: ' + userId);
"
```

## Step 2: Test Backend API

```
# Test auth endpoint
curl -X GET "https://<HOST>/api/auth/me" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Test protected endpoints
curl -X GET "https://<HOST>/api/rentals" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"

# Test admin endpoint (should be 403 for USER role)
curl -X GET "https://<HOST>/api/admin/users" \
  -H "Authorization: Bearer YOUR_SESSION_TOKEN"
```

Bootstrap an admin session for testing:

```
mongosh --eval "
use('test_database');
var adminId = 'admin-user-' + Date.now();
var adminToken = 'test_session_admin_' + Date.now();
db.users.insertOne({
  user_id: adminId,
  email: 'arpitchoudhary1911@gmail.com',
  name: 'Admin',
  picture: 'https://via.placeholder.com/150',
  role: 'ADMIN',
  blocked: false,
  created_at: new Date()
});
db.user_sessions.insertOne({
  user_id: adminId,
  session_token: adminToken,
  expires_at: new Date(Date.now() + 7*24*60*60*1000),
  created_at: new Date()
});
print('Admin session token: ' + adminToken);
"
```

## Step 3: Browser Testing (Playwright)

```
await page.context.add_cookies([{
    "name": "session_token",
    "value": "YOUR_SESSION_TOKEN",
    "domain": "<HOST>",
    "path": "/",
    "httpOnly": true,
    "secure": true,
    "sameSite": "None"
}]);
await page.goto("https://<HOST>/dashboard")
```

## Checklist
- [ ] User document has `user_id` (custom UUID), `role`, `blocked` fields
- [ ] Session `user_id` matches user's `user_id`
- [ ] Queries use `{"_id": 0}` projection
- [ ] `/api/auth/me` returns user data with role
- [ ] `/api/admin/*` returns 403 for USER role, 200 for ADMIN role
- [ ] Blocked users receive 403 on every protected route
- [ ] Rental data-scoping: USER can only see their own rentals, ADMIN sees all
