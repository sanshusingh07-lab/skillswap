# Testing checklist

## Automated smoke checks

The Flask test client should render `/`, `/about`, `/login`, `/register`, and `/admin/login`. With CSRF disabled only inside the test client, seeded student login should reach `/dashboard`, `/find-partners`, `/skills`, and `/profile`. Admin login should reach `/admin/dashboard`.

## Manual checks

Register with valid and invalid passwords, try a duplicate email, log in and log out, add and remove teaching and learning skills, search by skill and department, open a match explanation, send a request, accept it, message the connection, submit feedback, and verify unauthorized users are redirected.

Check responsive layouts at 320px, 375px, 768px, 1024px, and 1440px. Before deployment, add upload tests for JPG, JPEG, PNG, and WebP profile images and verify file-size limits.
