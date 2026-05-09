export default function StatusBadge({ value }) {
  const normalized = String(value || '').toLowerCase()
  let className = 'badge muted'

  if (['recorded', 'check_in', 'check_out', 'active', 'match_found'].includes(normalized)) {
    className = 'badge success'
  } else if (['duplicate_blocked', 'review_required'].includes(normalized)) {
    className = 'badge warning'
  } else if (['rejected', 'inactive', 'ignored'].includes(normalized)) {
    className = 'badge danger'
  }

  return <span className={className}>{value || '-'}</span>
}
