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
  {
    slug: 'examtry',
    title: 'ExamTry',
    provider: 'ExamLab',
    icon: 'ET',
    summary:
      'Launch a dedicated VM from snapshot 901 and practice through a live SSH terminal.',
    description:
      'Start an isolated virtual machine cloned from the ExamTry snapshot. The exam workspace connects to the VM over an authenticated SSH terminal streamed through Flask.',
    taskCount: 1,
    topics: ['VM provisioning', 'SSH terminal practice'],
    format: 'Interactive SSH terminal',
  },
]

export function getCatalogExam(slug: string | string[] | undefined): CatalogExam | undefined {
  if (typeof slug !== 'string') {
    return undefined
  }

  return catalogExams.find(exam => exam.slug === slug)
}
