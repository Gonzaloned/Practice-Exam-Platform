import { tasks } from './exam'

export interface CatalogExam {
  slug: string
  title: string
  provider: string
  icon: string
  summary: string
  description: string
  taskCount: number
  topics: string[]
  format: string
}

export const catalogExams: CatalogExam[] = [
  {
    slug: 'lfcs',
    title: 'Linux Foundation Certified System Administrator',
    provider: 'Linux Foundation',
    icon: 'LF',
    summary:
      'Practice core Linux system administration in a hands-on lab covering users, storage, networking, and services.',
    description:
      'Work through practical system administration tasks in a focused Linux environment. Configure users and permissions, manage storage, set up networking and services, and apply security settings.',
    taskCount: tasks.length,
    topics: [
      'User and group management',
      'File permissions',
      'Network configuration',
      'LVM and filesystems',
      'systemd services',
      'NFS',
      'SELinux',
    ],
    format: 'Hands-on Linux administration tasks',
  },
]

export function getCatalogExam(slug: string | string[] | undefined): CatalogExam | undefined {
  if (typeof slug !== 'string') {
    return undefined
  }

  return catalogExams.find(exam => exam.slug === slug)
}
