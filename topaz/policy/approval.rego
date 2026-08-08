package approval

import rego.v1

default allowed := false

allowed if {
  some role in data.approval.roles[input.resource.user]
  role in data.approval.permissions[input.resource.action]
}
