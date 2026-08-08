package access

import rego.v1

default allowed := false

allowed if {
  some role in data.access.roles[input.resource.user]
  role in data.access.permissions[input.resource.action]
}
