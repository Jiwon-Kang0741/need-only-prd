import { defineStore } from 'pinia';
import { ref } from 'vue';

import { fetchBookmarks, saveFavoriteMenuList } from '@/api/bookmark';
import { useToastMessage } from '@/composables/useToastMessage';

export interface BookmarkItem {
  menuId: string;
  menuNm: string;
}

const TOAST_MESSAGES = {
  ADD_SUCCESS: (title: string) => ({
    severity: 'success' as const,
    summary: 'Add to favorites',
    detail: `'${title}' has been added to your favorites.`,
    life: 3000,
  }),
  ADD_DUPLICATE: (title: string) => ({
    severity: 'warn' as const,
    summary: 'Failed to favorites',
    detail: `'${title}' is already in your favorites.`,
    life: 3000,
  }),
  REMOVE_SUCCESS: (title: string) => ({
    severity: 'success' as const,
    summary: 'Deleted to favorites',
    detail: `'${title}' has been removed from your favorites.`,
    life: 3000,
  }),
} as const;

export const useBookmarkStore = defineStore('bookmark', () => {
  const bookmarks = ref<BookmarkItem[]>([]);

  const setBookmarks = (newBookmarks: BookmarkItem[]) => {
    bookmarks.value = newBookmarks;
  };

  return {
    bookmarks,
    setBookmarks,
  };
});

export function useBookmark() {
  const store = useBookmarkStore();
  const { toast } = useToastMessage();

  async function loadBookmarks() {
    const response = await fetchBookmarks();

    if (response.header.responseCode === 'S0000') {
      const bookmarkData = response.payload.map((item) => ({
        menuId: item.menuId,
        menuNm: item.menuNm,
      }));
      store.setBookmarks(bookmarkData);
    }
  }

  async function addBookmark(bookmark: BookmarkItem) {
    const exists = store.bookmarks.some((el) => el.menuId === bookmark.menuId);

    if (exists) {
      return false;
    }

    const response = await saveFavoriteMenuList([
      {
        status: 'I',
        menuId: bookmark.menuId,
      },
    ]);

    if (response.header.responseCode === 'S0000') {
      await loadBookmarks();
      toast(TOAST_MESSAGES.ADD_SUCCESS(bookmark.menuNm));
    }

    return true;
  }

  async function removeBookmark(bookmark: BookmarkItem) {
    const exists = store.bookmarks.some((el) => el.menuId === bookmark.menuId);

    if (!exists) {
      return false;
    }

    const response = await saveFavoriteMenuList([
      {
        status: 'D',
        menuId: bookmark.menuId,
      },
    ]);

    if (response.header.responseCode === 'S0000') {
      await loadBookmarks();
      toast(TOAST_MESSAGES.REMOVE_SUCCESS(bookmark.menuNm));
    }

    return true;
  }

  const isBookmarked = (id: string) => {
    return store.bookmarks.some((bookmark) => bookmark.menuId === id);
  };

  const toggleBookmark = async (bookmark: BookmarkItem) => {
    if (isBookmarked(bookmark.menuId)) {
      await removeBookmark(bookmark);
    } else {
      await addBookmark(bookmark);
    }
  };

  return {
    bookmarks: store.bookmarks,
    loadBookmarks,
    addBookmark,
    removeBookmark,
    isBookmarked,
    toggleBookmark,
  };
}
