export function discussionLinkedTargetKey(target) {
  return `${target?.target_type || ''}:${target?.target_id || ''}`
}

async function switchSelectedCourseIfNeeded(userStore, target) {
  if (!target?.subject_id || !userStore.canSelectCourse) {
    return
  }
  if (String(userStore.selectedCourse?.id || '') === String(target.subject_id)) {
    return
  }
  const courses = await userStore.fetchTeachingCourses(false)
  const match = courses.find(item => String(item.id) === String(target.subject_id))
  if (match) {
    userStore.setSelectedCourse(match)
  }
}

function resolveDiscussionLinkedTargetRoute(target, userStore) {
  if (!target?.target_type || !target?.target_id) {
    return null
  }
  if (target.target_type === 'homework') {
    if (userStore.isStudent || userStore.isAdmin) {
      return { name: 'HomeworkSubmit', params: { id: String(target.target_id) } }
    }
    return { name: 'HomeworkSubmissions', params: { id: String(target.target_id) } }
  }
  if (target.target_type === 'material') {
    return { name: 'MaterialRead', params: { id: String(target.target_id) } }
  }
  if (target.target_type === 'learning_note') {
    return { name: 'LearningNotes', query: { note: String(target.target_id) } }
  }
  return null
}

export async function openDiscussionLinkedTarget(target, router, userStore) {
  if (!target?.available) {
    return
  }
  await switchSelectedCourseIfNeeded(userStore, target)
  const route = resolveDiscussionLinkedTargetRoute(target, userStore)
  if (!route) {
    return
  }
  await router.push(route)
}
