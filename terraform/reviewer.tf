# ─── Read-only reviewer account for the Head of IT ───────────────────────────

resource "aws_iam_user" "reviewer" {
  name = "massy-reviewer"
}

resource "aws_iam_user_policy_attachment" "reviewer_readonly" {
  user       = aws_iam_user.reviewer.name
  policy_arn = "arn:aws:iam::aws:policy/ReadOnlyAccess"
}

resource "aws_iam_user_login_profile" "reviewer" {
  user                    = aws_iam_user.reviewer.name
  password_reset_required = false
}

output "reviewer_username" {
  value = aws_iam_user.reviewer.name
}

output "reviewer_password" {
  value     = aws_iam_user_login_profile.reviewer.password
  sensitive = true
}

output "reviewer_console_url" {
  value = "https://${data.aws_caller_identity.current.account_id}.signin.aws.amazon.com/console"
}

data "aws_caller_identity" "current" {}
