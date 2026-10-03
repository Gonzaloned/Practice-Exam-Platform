export type Task = {
  id: number
  title: string
  category: string
  description: string
  requirements: string[]
  status: 'done' | 'current' | 'pending'
}

export const tasks: Task[] = [
  {
    id: 1,
    title: 'User management',
    category: 'Users',
    description: 'Create a local user account with the required group membership.',
    requirements: ['Create user "student"', 'Add the user to the wheel group', 'Set a password'],
    status: 'done'
  },
  {
    id: 2,
    title: 'File permissions',
    category: 'Permissions',
    description: 'Configure ownership and permissions for the application directory.',
    requirements: ['Owner: root', 'Group: developers', 'Directory mode: 2775'],
    status: 'done'
  },
  {
    id: 3,
    title: 'Network configuration',
    category: 'Networking',
    description: 'Configure a persistent static IPv4 address on the required interface.',
    requirements: ['Address: 192.168.100.20/24', 'Gateway: 192.168.100.1', 'DNS: 1.1.1.1'],
    status: 'done'
  },
  {
    id: 4,
    title: 'Create an LVM volume',
    category: 'Storage',
    description: 'Create and mount an LVM logical volume according to the requirements below.',
    requirements: ['Create volume group "vg_data"', 'Create logical volume "data"', 'Size: 5 GiB', 'Format as XFS', 'Mount persistently at /data'],
    status: 'current'
  },
  {
    id: 5,
    title: 'Filesystem configuration',
    category: 'Storage',
    description: 'Configure a persistent filesystem mount with the requested mount options.',
    requirements: ['Use /etc/fstab', 'Mount point: /srv/data', 'Verify the mount'],
    status: 'pending'
  },
  {
    id: 6,
    title: 'systemd service',
    category: 'systemd',
    description: 'Configure a custom systemd service and make it start automatically.',
    requirements: ['Create the unit file', 'Enable the service', 'Start the service', 'Verify status'],
    status: 'pending'
  },
  {
    id: 7,
    title: 'NFS configuration',
    category: 'Networking',
    description: 'Export a directory using NFS with the requested permissions.',
    requirements: ['Export /srv/nfs', 'Allow the lab network', 'Reload exports', 'Verify with exportfs'],
    status: 'pending'
  },
  {
    id: 8,
    title: 'SELinux context',
    category: 'Security',
    description: 'Configure the appropriate SELinux context for a web application directory.',
    requirements: ['Set the persistent context', 'Apply the context', 'Verify with ls -Z'],
    status: 'pending'
  }
]
